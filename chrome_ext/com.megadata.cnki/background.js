/*
* CREATED DATE: Fri Apr  4 02:05:22 2025
* CREATED BY: qiangxu, toxuqiang@gmail.com
*/
//==============================================================================
// background.js - 后台脚本，使用任务队列管理下载流程
//==============================================================================

// 引入YAML解析库
importScripts('js-yaml.min.js');

// 全局状态变量
let taskQueue = [];  // 任务队列
let isRunning = false;  // 是否运行自动化流程
let isProcessingQueue = false;  // 是否正在处理队列
let config = null;  // 配置信息
let activeTabId = null;  // 活跃的标签页ID
let queueTimer = null;  // 队列处理定时器

// 下载统计
let downloadStats = {
    totalFiles: 0,
    completedFiles: 0,
    successFiles: 0,
    failedFiles: 0,
    currentFile: '',
    currentUrl: ''
};

// 状态消息
let statusMessage = '';

// 任务类型枚举
const TaskType = {
    SCAN_DIRECTORY: 'scanDirectory',
    PROCESS_FILE: 'processFile',
    DOWNLOAD_PAPER: 'downloadPaper'
};

// 扩展安装或更新时初始化
chrome.runtime.onInstalled.addListener(() => {
    console.log('知网下载链接提取器已安装/更新');

    // 初始化存储默认设置
    chrome.storage.local.set({
        downloadInterval: 3,  // 默认下载间隔为3秒
        isRunning: false,
        taskQueue: [],
        downloadStats: {
            totalFiles: 0,
            completedFiles: 0,
            successFiles: 0,
            failedFiles: 0,
            currentFile: ''
        }
    });

    // 加载配置文件
    loadConfig();
});

// 加载并解析配置文件
function loadConfig() {
    console.log('尝试加载配置文件...');

    // 使用fetch API获取配置文件
    fetch(chrome.runtime.getURL('config.yaml'))
        .then(response => {
            if (!response.ok) {
                throw new Error(`无法加载配置文件: ${response.status}`);
            }
            return response.text();
        })
        .then(yamlText => {
            try {
                // 解析YAML
                config = jsyaml.load(yamlText);
                console.log('成功加载配置:', config);

                // 验证配置
                if (!config.ndjson_dir) {
                    console.warn('配置文件中缺少ndjson_dir字段，使用默认值./ndjson');
                    config.ndjson_dir = './ndjson';
                }

                // 设置下载间隔
                if (config.download_interval) {
                    chrome.storage.local.set({ downloadInterval: config.download_interval });
                }

                // 更新存储中的配置
                chrome.storage.local.set({ config: config });
            } catch (e) {
                console.error('解析配置文件时出错:', e);
                setStatusMessage('配置文件解析失败: ' + e.message);
            }
        })
        .catch(error => {
            console.error('加载配置文件失败:', error);
            setStatusMessage('加载配置文件失败: ' + error.message);
        });
}

// 设置状态消息
function setStatusMessage(message) {
    statusMessage = message;
    console.log('状态更新:', message);
    // 更新存储中的状态消息
    chrome.storage.local.set({ statusMessage: message });
}

// 更新下载统计
function updateDownloadStats(updates) {
    downloadStats = { ...downloadStats, ...updates };
    console.log('下载统计更新:', downloadStats);
    // 更新存储中的下载统计
    chrome.storage.local.set({ downloadStats: downloadStats });
}

// 添加任务到队列
function addTask(type, data) {
    const task = { type, data, addedTime: Date.now() };
    taskQueue.push(task);
    
    // 更新存储
    chrome.storage.local.set({ taskQueue: taskQueue });
    
    console.log(`添加任务到队列: ${type}`, data);
    
    // 如果队列处理器没有运行，启动它
    if (!isProcessingQueue && isRunning) {
        processQueue();
    }
}

// 开始自动化流程
function startAutomation() {
    if (isRunning) {
        console.log('自动化流程已经在运行中');
        return;
    }

    isRunning = true;
    chrome.storage.local.set({ isRunning: true });
    setStatusMessage('自动化流程已启动');

    // 添加初始扫描任务
    addTask(TaskType.SCAN_DIRECTORY, {});
    
    // 启动队列处理器
    processQueue();
}

// 停止自动化流程
function stopAutomation() {
    if (!isRunning) {
        console.log('自动化流程已经停止');
        return;
    }

    isRunning = false;

    // 清除定时器
    if (queueTimer) {
        clearTimeout(queueTimer);
        queueTimer = null;
    }

    isProcessingQueue = false;
    chrome.storage.local.set({ isRunning: false });
    setStatusMessage('自动化流程已停止');
}

// 清空所有数据
function clearAllData() {
    // 停止所有活动
    stopAutomation();

    // 重置所有状态变量
    taskQueue = [];
    
    // 重置下载统计
    downloadStats = {
        totalFiles: 0,
        completedFiles: 0,
        successFiles: 0,
        failedFiles: 0,
        currentFile: ''
    };

    // 清空存储
    chrome.storage.local.set({
        isRunning: false,
        taskQueue: [],
        downloadStats: downloadStats,
        statusMessage: '所有数据已清空'
    });

    setStatusMessage('所有数据已清空');
}

// 队列处理器 - 核心调度函数
function processQueue() {
    if (!isRunning) {
        console.log('自动化已停止，终止队列处理');
        isProcessingQueue = false;
        return;
    }
    
    if (isProcessingQueue) {
        console.log('队列处理器已在运行');
        return;
    }
    
    isProcessingQueue = true;
    
    // 检查队列是否为空
    if (taskQueue.length === 0) {
        console.log('任务队列为空，添加扫描任务');
        addTask(TaskType.SCAN_DIRECTORY, {});
        isProcessingQueue = false;
        return;
    }
    
    // 获取并移除队列中的第一个任务
    const task = taskQueue.shift();
    chrome.storage.local.set({ taskQueue: taskQueue });
    
    console.log(`处理任务: ${task.type}`, task.data);
    
    // 根据任务类型执行相应的操作
    switch (task.type) {
        case TaskType.SCAN_DIRECTORY:
            executeScandirectory();
            break;
            
        case TaskType.PROCESS_FILE:
            executeProcessFile(task.data.filename);
            break;
            
        case TaskType.DOWNLOAD_PAPER:
            executeDownloadPaper(task.data.paper);
            break;
            
        default:
            console.error(`未知任务类型: ${task.type}`);
            isProcessingQueue = false;
            processQueueAfterDelay(1); // 遇到错误，短暂延迟后继续处理队列
    }
}

// 扫描目录执行器
function executeScandirectory() {
    if (!isRunning) {
        isProcessingQueue = false;
        return;
    }

    if (!config || !config.ndjson_dir) {
        setStatusMessage('配置错误: 未指定NDJSON目录');
        isProcessingQueue = false;
        processQueueAfterDelay(10);
        return;
    }

    console.log(`扫描目录: ${config.ndjson_dir}`);
    setStatusMessage(`正在扫描目录: ${config.ndjson_dir}`);

    // 使用Native Messaging与本地应用通信
    chrome.runtime.sendNativeMessage('com.megadata.cnki', { 
        action: 'scanDirectory', 
        path: config.ndjson_dir 
    }, 
    function(response) {
        if (chrome.runtime.lastError) {
            console.error('与本地应用通信失败:', chrome.runtime.lastError);
            setStatusMessage('扫描目录失败: 与本地应用通信失败');
            isProcessingQueue = false;
            
            // 一段时间后重新扫描
            processQueueAfterDelay(config.download_interval || 10);
            return;
        }

        if (!response || !response.success) {
            console.error('扫描目录失败:', response?.error || '未知错误');
            setStatusMessage('扫描目录失败: ' + (response?.error || '未知错误'));
            isProcessingQueue = false;
            
            // 一段时间后重新扫描
            processQueueAfterDelay(config.download_interval || 10);
            return;
        }

        // 筛选JSON和NDJSON文件
        const jsonFiles = (response.files || [])
            .filter(file => file.endsWith('.json') || file.endsWith('.ndjson'));

        console.log(`找到${jsonFiles.length}个JSON文件`);
        setStatusMessage(`找到 ${jsonFiles.length} 个JSON文件`);

        // 更新下载统计中的总文件数
        updateDownloadStats({
            totalFiles: downloadStats.totalFiles + jsonFiles.length
        });

        // 为每个文件添加处理任务
        if (jsonFiles.length > 0) {
            jsonFiles.forEach(filename => {
                addTask(TaskType.PROCESS_FILE, { filename });
            });
        } else {
            // 没有文件，一段时间后重新扫描
            const interval = config.download_interval || 10;
            setStatusMessage(`没有发现新文件，${interval} 秒后重新扫描`);
            addTask(TaskType.SCAN_DIRECTORY, {});
        }
        
        isProcessingQueue = false;
        processQueueAfterDelay(1); // 短暂延迟后继续处理队列
    });
}

// 处理文件执行器
function executeProcessFile(filename) {
    if (!isRunning) {
        isProcessingQueue = false;
        return;
    }

    console.log(`处理文件: ${filename}`);
    setStatusMessage(`正在处理文件: ${filename}`);

    // 更新当前处理的文件名
    updateDownloadStats({
        currentFile: filename
    });

    // 读取JSON文件内容
    chrome.runtime.sendNativeMessage('com.megadata.cnki', 
        { 
            action: 'readFile', 
            path: `${config.ndjson_dir}/${filename}` 
        }, 
        function(response) {
            if (chrome.runtime.lastError || !response || !response.success) {
                console.error('读取文件失败:', chrome.runtime.lastError || response?.error || '未知错误');
                setStatusMessage(`读取文件失败: ${chrome.runtime.lastError?.message || response?.error || '未知错误'}`);
                isProcessingQueue = false;
                processQueueAfterDelay(1);
                return;
            }

            try {
                // 解析NDJSON内容
                const lines = response.content.split('\n').filter(line => line.trim());
                const papers = [];

                lines.forEach((line, index) => {
                    try {
                        const paper = JSON.parse(line);
                        if (paper.title && paper.url) {
                            papers.push({
                                title: paper.title,
                                url: paper.url,
                                authors: paper.authors || '',
                                source: paper.dbname || paper.source || '',
                                date: paper.date || '',
                                filename: paper.filename || '',
                                sourceFile: filename // 添加源文件信息
                            });
                        }
                    } catch (lineError) {
                        console.error(`解析第${index + 1}行时出错:`, lineError);
                    }
                });

                if (papers.length > 0) {
                    console.log(`从文件中解析出${papers.length}篇论文`);
                    setStatusMessage(`从文件中解析出 ${papers.length} 篇论文，准备下载`);

                    // 重置下载统计，仅针对当前文件的论文
                    resetDownloadStats(papers.length);

                    // 为每篇论文添加下载任务
                    papers.forEach(paper => {
                        addTask(TaskType.DOWNLOAD_PAPER, { paper });
                    });
                } else {
                    console.warn('文件中没有有效的论文数据');
                    setStatusMessage('文件中没有有效的论文数据');

                    // 如果配置了下载后删除，则删除文件
                    if (config.delete_after_download) {
                        deleteFile(filename);
                    }
                }
            } catch (error) {
                console.error('解析文件内容时出错:', error);
                setStatusMessage(`解析文件内容时出错: ${error.message}`);
            }
            
            isProcessingQueue = false;
            processQueueAfterDelay(1);
        }
    );
}

// 下载论文执行器
function executeDownloadPaper(paper) {
    if (!isRunning) {
        isProcessingQueue = false;
        return;
    }

    console.log(`尝试下载: ${paper.title}`);
    setStatusMessage(`尝试下载: ${paper.title}`);

    // 更新当前正在下载的URL
    updateDownloadStats({
        currentUrl: paper.url
    });

    // 获取当前激活的标签页
    chrome.tabs.query({}, tabs => {
        let knownTabFound = false;

        // 尝试找到知网相关标签页
        for (const tab of tabs) {
            if ((tab.url && tab.url.includes('kns8s/defaultresult')) || tab.url == "http://www-cnki-net-s.webvpn.zju.edu.cn:8001/") {
            //if ((tab.url && tab.url.includes('kns8s/defaultresult'))){
                activeTabId = tab.id;
                knownTabFound = true;
                break;
            }
        }

        if (!knownTabFound) {
            console.log('未找到知网标签页，请打开知网');
            setStatusMessage('未找到知网标签页，请打开知网');
            isProcessingQueue = false;
            
            // 稍后再试
            setTimeout(() => {
                // 重新添加当前任务
                addTask(TaskType.DOWNLOAD_PAPER, { paper });
                processQueue();
            }, 5000);
            
            return;
        }

        // 确保content script注入
        chrome.scripting.executeScript({
            target: { tabId: activeTabId },
            files: ['content.js']
        }).then(() => {
            // 发送模拟点击消息
			console.log("simulateClick", activeTabId, paper.url, paper.title)

            chrome.tabs.sendMessage(activeTabId, {
                action: "simulateClick",
                url: paper.url,
                title: paper.title
            }, function(response) {
                if (chrome.runtime.lastError) {
                    console.error('发送消息失败:', chrome.runtime.lastError.message);
                    console.error('错误详情:', JSON.stringify(chrome.runtime.lastError));
                } else if (!response || !response.success) {
                    console.error('模拟点击失败');
                } else {
                    console.log('模拟点击成功');
                    
                    // 更新下载统计
                    updateDownloadStats({
                        completedFiles: downloadStats.completedFiles + 1,
                        successFiles: downloadStats.successFiles + 1
                    });
                }
                
                // 检查是否是文件中的最后一个论文
                const remainingTasks = taskQueue.filter(task => 
                    task.type === TaskType.DOWNLOAD_PAPER && 
                    task.data.paper.sourceFile === paper.sourceFile
                ).length;
                
                if (remainingTasks === 0) {
                    console.log(`文件 ${paper.sourceFile} 中的所有论文已下载完成`);
                    setStatusMessage(`文件 ${paper.sourceFile} 中的所有论文已下载完成`);
                    
                    // 如果配置了下载后删除，则删除文件
                    if (config.delete_after_download) {
                        deleteFile(paper.sourceFile);
                    }
                }
                
                isProcessingQueue = false;
                
                // 使用下载间隔
                const interval = config?.download_interval || 3;
                processQueueAfterDelay(interval);
            });
			/*
            isProcessingQueue = false;
			const interval = config?.download_interval || 3;
			processQueueAfterDelay(interval);
			*/

        }).catch(error => {
            console.error('注入脚本失败:', error);
            isProcessingQueue = false;
            processQueueAfterDelay(3);
        });
    });
}

// 一段时间后处理队列
function processQueueAfterDelay(seconds) {
    const delay = seconds * 1000;
    
    // 清除可能存在的定时器
    if (queueTimer) {
        clearTimeout(queueTimer);
    }
    
    queueTimer = setTimeout(() => {
        processQueue();
    }, delay);
}

// 重置下载统计
function resetDownloadStats(totalCount) {
    downloadStats = {
        totalFiles: totalCount,
        completedFiles: 0,
        successFiles: 0,
        failedFiles: 0,
        currentFile: downloadStats.currentFile,
        currentUrl: ""
    };

    // 更新存储
    chrome.storage.local.set({ downloadStats: downloadStats });
}

// 删除文件
function deleteFile(filename) {
    console.log(`删除文件: ${filename}`);
    setStatusMessage(`正在删除文件: ${filename}`);

    chrome.runtime.sendNativeMessage('com.megadata.cnki', 
        { 
            action: 'deleteFile', 
            path: `${config.ndjson_dir}/${filename}` 
        }, 
        function(response) {
            if (chrome.runtime.lastError || !response || !response.success) {
                console.error('删除文件失败:', chrome.runtime.lastError || response?.error || '未知错误');
                setStatusMessage(`删除文件失败: ${chrome.runtime.lastError?.message || response?.error || '未知错误'}`);
            } else {
                console.log('文件删除成功');
                setStatusMessage(`文件 ${filename} 删除成功`);
            }
        }
    );
}

// 监听来自popup或content script的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    // 处理各种请求
    if (request.action === "startAutomation") {
        console.log("收到开始自动化请求");
        startAutomation();
        sendResponse({success: true});
        return true;
    } 
    else if (request.action === "stopAutomation") {
        console.log("收到停止自动化请求");
        stopAutomation();
        sendResponse({success: true});
        return true;
    }
    else if (request.action === "clearAllData") {
        console.log("收到清空所有数据请求");
        clearAllData();
        sendResponse({success: true});
        return true;
    }
    else if (request.action === "getDownloadStatus") {
        console.log("收到获取下载状态请求");
        
        const pendingPapers = taskQueue.filter(task => task.type === TaskType.DOWNLOAD_PAPER).length;
        const pendingFiles = taskQueue.filter(task => task.type === TaskType.PROCESS_FILE).length;

        sendResponse({
            isRunning: isRunning,
            isProcessingQueue: isProcessingQueue,
            pendingPapers: pendingPapers,
            pendingFiles: pendingFiles,
            activeTabId: activeTabId,
            totalFiles: downloadStats.totalFiles,
            completedFiles: downloadStats.completedFiles,
            successFiles: downloadStats.successFiles,
            failedFiles: downloadStats.failedFiles,
            currentFile: downloadStats.currentFile,
            currentUrl: downloadStats.currentUrl,
            statusMessage: statusMessage
        });

        return true; // 表示已处理
    }
});

// 设置content script注入
function setupContentScriptInjection() {
    // 定义需要监听的域名和路径组合
    const urlPatterns = [
        // 普通域名匹配
        { hostContains: '122.51.45.239' },
        // 特定路径匹配
        { hostContains: '.webvpn.zju.edu.cn', pathContains: 'kns8s/defaultresult' },
    ];
    
    // 为每个URL模式设置监听器
    urlPatterns.forEach(pattern => {
        console.log(`设置对URL模式的监听:`, pattern);
        
        chrome.webNavigation.onCompleted.addListener(
            function(details) {
                console.log(`页面加载完成: ${details.url}, tabId: ${details.tabId}`);
            
                // 页面加载完成后注入 content script
                chrome.scripting.executeScript({
                    target: { tabId: details.tabId },
                    files: ['content.js']
                })
                    .then(() => {
                        console.log(`内容脚本成功注入到标签页 ${details.tabId}`);
                    })
                    .catch(error => console.error(`内容脚本注入失败: ${error}`));
            }, 
            { url: [pattern] }
        );
    });
}

// 在扩展启动时设置监听
setupContentScriptInjection();

// 初始化时检查是否有未完成的任务队列并加载配置
chrome.storage.local.get(['isRunning', 'taskQueue', 'downloadStats'], 
    function(data) {
        // 恢复下载统计
        if (data.downloadStats) {
            downloadStats = data.downloadStats;
        }

        // 恢复任务队列
        if (data.taskQueue && Array.isArray(data.taskQueue)) {
            taskQueue = data.taskQueue;
        }

        // 首先加载配置
        loadConfig();

        // 恢复自动化状态
        if (data.isRunning) {
            isRunning = false;
            // 不自动启动，需要用户手动启动
            // startAutomation();
        }
    }
);
