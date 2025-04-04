/*
* CREATED DATE: Fri Apr  4 02:05:22 2025
* CREATED BY: qiangxu, toxuqiang@gmail.com
*/
//==============================================================================
// background.js - 后台脚本，负责管理下载队列和协调标签页
//==============================================================================

// 引入YAML解析库
importScripts('js-yaml.min.js');

// 全局状态变量
let state = {
    config: null,
    activeTabId: null,
    isRunning: false,
    downloadTimer: null,
    
    // 文件处理状态
    filesToProcess: [],
    currentFile: null,
    
    // 下载队列状态
    downloadQueue: [],
    isDownloading: false,
    currentDownloadIndex: 0,
    
    // 下载统计
    stats: {
        totalFiles: 0,
        completedFiles: 0,
        successFiles: 0,
        failedFiles: 0,
        currentFile: '',
        currentUrl: ''
    },
    
    // 状态消息
    statusMessage: ''
};

// 扩展安装或更新时初始化
chrome.runtime.onInstalled.addListener(() => {
    console.log('知网下载链接提取器已安装/更新');

    // 初始化存储默认设置
    chrome.storage.local.set({
        downloadInterval: 3,  // 默认下载间隔为3秒
        isDownloading: false,
        isRunning: false,
        downloadQueue: [],
        currentIndex: 0,
        paperLinks: {},
        processingFiles: [],
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
                state.config = jsyaml.load(yamlText);
                console.log('成功加载配置:', state.config);

                // 验证配置
                if (!state.config.ndjson_dir) {
                    console.warn('配置文件中缺少ndjson_dir字段，使用默认值./ndjson');
                    state.config.ndjson_dir = './ndjson';
                }

                // 设置下载间隔
                if (state.config.download_interval) {
                    chrome.storage.local.set({ downloadInterval: state.config.download_interval });
                }

                // 更新存储中的配置
                chrome.storage.local.set({ config: state.config });
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
    state.statusMessage = message;
    console.log('状态更新:', message);
    // 更新存储中的状态消息
    chrome.storage.local.set({ statusMessage: message });
}

// 更新下载统计
function updateStats(updates) {
    state.stats = { ...state.stats, ...updates };
    console.log('下载统计更新:', state.stats);
    // 更新存储中的下载统计
    chrome.storage.local.set({ downloadStats: state.stats });
}

//==============================================================================
// 核心自动化流程控制
//==============================================================================

// 开始自动化流程
function startAutomation() {
    if (state.isRunning) {
        console.log('自动化流程已经在运行中');
        return;
    }

    state.isRunning = true;
    chrome.storage.local.set({ isRunning: true });
    setStatusMessage('自动化流程已启动');

    // 开始自动化流程循环
    automationLoop();
}

// 停止自动化流程
function stopAutomation() {
    if (!state.isRunning) {
        console.log('自动化流程已经停止');
        return;
    }

    state.isRunning = false;

    // 如果有正在进行的下载，停止它
    if (state.isDownloading && state.downloadTimer) {
        clearTimeout(state.downloadTimer);
        state.downloadTimer = null;
        state.isDownloading = false;
    }

    chrome.storage.local.set({ 
        isRunning: false,
        isDownloading: false
    });

    setStatusMessage('自动化流程已停止');
}

// 清空所有数据
function clearAllData() {
    // 停止所有活动
    stopAutomation();

    // 重置所有状态变量
    state.downloadQueue = [];
    state.currentDownloadIndex = 0;
    state.filesToProcess = [];
    state.currentFile = null;

    // 重置下载统计
    state.stats = {
        totalFiles: 0,
        completedFiles: 0,
        successFiles: 0,
        failedFiles: 0,
        currentFile: ''
    };

    // 清空存储
    chrome.storage.local.set({
        isDownloading: false,
        isRunning: false,
        downloadQueue: [],
        currentIndex: 0,
        paperLinks: {},
        processingFiles: [],
        downloadStats: state.stats,
        statusMessage: '所有数据已清空'
    });

    setStatusMessage('所有数据已清空');
}

//==============================================================================
// 主要自动化循环 - 简化了整体流程
//==============================================================================

// 主要自动化循环 - 根据当前状态决定下一步操作
function automationLoop() {
    if (!state.isRunning) {
        console.log('自动化流程已停止');
        return;
    }

    console.log('自动化循环: 检查当前状态');
    
    // 优先级顺序:
    // 1. 如果正在下载中，继续处理队列
    // 2. 如果有文件队列但没有下载，开始处理第一个文件
    // 3. 如果没有文件队列，扫描目录
    
    if (state.isDownloading && state.downloadQueue.length > 0) {
        console.log('自动化循环: 继续处理当前下载队列');
        // 下载队列已经在进行中，不需要额外操作
        // processDownloadItem() 函数会在处理完当前项后自动调用下一个
    }
    else if (state.currentFile) {
        console.log('自动化循环: 正在处理文件，等待完成');
        // 正在处理文件，等待处理完成
    }
    else if (state.filesToProcess.length > 0) {
        console.log('自动化循环: 开始处理下一个文件');
        processNextFile();
    }
    else {
        console.log('自动化循环: 扫描目录寻找新文件');
        scanDirectory();
    }
}

//==============================================================================
// 目录扫描和文件处理
//==============================================================================

// 扫描NDJSON目录
function scanDirectory() {
    if (!state.isRunning) {
        console.log('自动化已停止，终止扫描');
        return;
    }

    if (!state.config || !state.config.ndjson_dir) {
        setStatusMessage('配置错误: 未指定NDJSON目录');
        return;
    }

    console.log(`扫描目录: ${state.config.ndjson_dir}`);
    setStatusMessage(`正在扫描目录: ${state.config.ndjson_dir}`);

    // 使用Native Messaging与本地应用通信
    chrome.runtime.sendNativeMessage('com.cnki.downloader.bak', { 
        action: 'scanDirectory', 
        path: state.config.ndjson_dir 
    }, 
    function(response) {
        if (chrome.runtime.lastError) {
            console.error('与本地应用通信失败:', chrome.runtime.lastError);
            setStatusMessage('扫描目录失败: 与本地应用通信失败');

            // 如果自动化仍在运行，尝试在一段时间后重新扫描
            scheduleNextAction(() => automationLoop());
            return;
        }

        if (!response || !response.success) {
            console.error('扫描目录失败:', response?.error || '未知错误');
            setStatusMessage('扫描目录失败: ' + (response?.error || '未知错误'));

            // 如果自动化仍在运行，尝试在一段时间后重新扫描
            scheduleNextAction(() => automationLoop());
            return;
        }

        // 筛选JSON和NDJSON文件
        state.filesToProcess = (response.files || [])
            .filter(file => file.endsWith('.json') || file.endsWith('.ndjson'));

        console.log(`找到${state.filesToProcess.length}个JSON文件`);
        setStatusMessage(`找到 ${state.filesToProcess.length} 个JSON文件`);

        // 更新下载统计中的总文件数
        updateStats({
            totalFiles: state.stats.totalFiles + state.filesToProcess.length
        });
        
        // 更新存储
        chrome.storage.local.set({
            processingFiles: state.filesToProcess
        });

        // 继续自动化循环
        automationLoop();
    });
}

// 处理下一个文件
function processNextFile() {
    if (!state.isRunning) {
        console.log('自动化已停止，终止处理');
        return;
    }

    if (state.filesToProcess.length === 0) {
        console.log('没有更多的JSON文件需要处理');
        setStatusMessage('所有文件处理完成，等待重新扫描');

        // 等待配置的间隔时间后重新扫描
        scheduleNextAction(() => automationLoop());
        return;
    }

    state.currentFile = state.filesToProcess.shift();
    console.log(`处理文件: ${state.currentFile}`);
    setStatusMessage(`正在处理文件: ${state.currentFile}`);

    // 更新当前处理的文件名
    updateStats({
        currentFile: state.currentFile
    });

    // 更新存储状态
    chrome.storage.local.set({
        processingFiles: state.filesToProcess,
        currentProcessingFile: state.currentFile
    });

    // 读取JSON文件内容
    chrome.runtime.sendNativeMessage('com.cnki.downloader.bak', 
        { 
            action: 'readFile', 
            path: `${state.config.ndjson_dir}/${state.currentFile}` 
        }, 
        function(response) {
            if (chrome.runtime.lastError || !response || !response.success) {
                console.error('读取文件失败:', chrome.runtime.lastError || response?.error || '未知错误');
                setStatusMessage(`读取文件失败: ${chrome.runtime.lastError?.message || response?.error || '未知错误'}`);

                // 文件读取失败，继续循环
                state.currentFile = null;
                automationLoop();
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
                                filename: paper.filename || ''
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
                    state.stats = {
                        totalFiles: papers.length,
                        completedFiles: 0,
                        successFiles: 0,
                        failedFiles: 0,
                        currentFile: state.currentFile,
                        currentUrl: ""
                    };
                    
                    // 更新存储
                    chrome.storage.local.set({ downloadStats: state.stats });

                    // 准备下载队列
                    prepareDownload(papers);
                } else {
                    console.warn('文件中没有有效的论文数据');
                    setStatusMessage('文件中没有有效的论文数据');

                    // 如果配置了下载后删除，则删除文件
                    if (state.config.delete_after_download) {
                        deleteProcessedFile();
                    } else {
                        // 文件处理完成，继续循环
                        state.currentFile = null;
                        automationLoop();
                    }
                }
            } catch (error) {
                console.error('解析文件内容时出错:', error);
                setStatusMessage(`解析文件内容时出错: ${error.message}`);

                // 文件解析失败，继续循环
                state.currentFile = null;
                automationLoop();
            }
        }
    );
}

//==============================================================================
// 下载队列处理
//==============================================================================

// 准备下载队列
function prepareDownload(papers) {
    if (!state.isRunning) {
        console.log('自动化已停止，终止下载准备');
        return;
    }

    // 获取当前激活的标签页
    chrome.tabs.query({}, tabs => {
        let knownTabFound = false;

        // 尝试找到知网相关标签页
        for (const tab of tabs) {
            if (tab.url && (
                tab.url.includes('kns8s/defaultresult')
            )) {
                state.activeTabId = tab.id;
                knownTabFound = true;
                break;
            }
        }

        if (!knownTabFound) {
            console.log('未找到知网标签页，请打开知网');
            setStatusMessage('未找到知网标签页，请打开知网');
            
            // 标签页问题，等待一段时间后重试
            scheduleNextAction(() => prepareDownload(papers));
            return;
        }

        // 初始化下载队列
        state.downloadQueue = papers;
        state.currentDownloadIndex = 0;
        state.isDownloading = true;

        // 更新存储状态
        chrome.storage.local.set({
            downloadQueue: state.downloadQueue,
            currentIndex: state.currentDownloadIndex,
            isDownloading: state.isDownloading
        });

        // 开始处理下载队列
        processDownloadItem();
    });
}

// 处理下载队列中的当前项
function processDownloadItem() {
    console.log(`===================================`);
    console.log(`开始处理下载队列项 #${state.currentDownloadIndex + 1}`);
    console.log(`当前队列长度: ${state.downloadQueue.length}`);
    console.log(`===================================`);

    if (!state.isRunning) {
        console.log('自动化已停止，终止下载');
        state.isDownloading = false;
        chrome.storage.local.set({ isDownloading: false });
        return;
    }

    // 检查是否已完成或停止
    if (!state.isDownloading || state.downloadQueue.length === 0 || 
        state.currentDownloadIndex >= state.downloadQueue.length) {
        console.log('当前文件的下载队列已完成');
        state.isDownloading = false;

        // 文件所有论文处理完成
        setStatusMessage(`文件 ${state.currentFile} 中的所有论文已下载完成`);

        // 更新存储
        chrome.storage.local.set({
            isDownloading: false,
            downloadQueue: [],
            currentIndex: 0
        });

        // 文件处理完成，删除该文件
        if (state.currentFile && state.config.delete_after_download) {
            deleteProcessedFile();
        } else {
            // 文件处理完成，继续循环
            state.currentFile = null;
            automationLoop();
        }
        
        return;
    }

    // 获取当前下载项
    const paper = state.downloadQueue[state.currentDownloadIndex];
    console.log(`正在下载: ${paper.title}`);
    setStatusMessage(`正在下载: ${paper.title}`);

    // 检查标签页是否还存在
    chrome.tabs.get(state.activeTabId, tab => {
        if (chrome.runtime.lastError || !tab) {
            console.log('原始标签页已关闭，请打开知网');
            setStatusMessage('原始标签页已关闭，请打开知网');
            
            // 标签页问题，等待一段时间后重试
            scheduleNextAction(() => processDownloadItem());
            return;
        }

        // 更新当前正在下载的URL
        updateStats({ currentUrl: paper.url });

        // 确保content script注入
        chrome.scripting.executeScript({
            target: { tabId: state.activeTabId },
            files: ['content.js']
        }).then(() => {
            // 发送模拟点击消息
            chrome.tabs.sendMessage(state.activeTabId, {
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
                }
                
                // 更新下载统计
                updateStats({
                    completedFiles: state.stats.completedFiles + 1,
                    successFiles: response && response.success ? 
                        state.stats.successFiles + 1 : state.stats.successFiles,
                    failedFiles: !response || !response.success ? 
                        state.stats.failedFiles + 1 : state.stats.failedFiles
                });
                
                // 更新索引
                state.currentDownloadIndex++;
                chrome.storage.local.set({ currentIndex: state.currentDownloadIndex });
                
                // 安排下一个下载
                const interval = state.config?.download_interval || 3;
                scheduleNextAction(() => processDownloadItem(), interval);
            });
        }).catch(error => {
            console.error('注入脚本失败:', error);
            
            // 脚本注入失败，继续下一个
            state.currentDownloadIndex++;
            chrome.storage.local.set({ currentIndex: state.currentDownloadIndex });
            
            const interval = state.config?.download_interval || 3;
            scheduleNextAction(() => processDownloadItem(), interval);
        });
    });
}

//==============================================================================
// 辅助函数
//==============================================================================

// 安排下一个动作
function scheduleNextAction(action, intervalSeconds = null) {
    if (!state.isRunning) return;
    
    // 如果没有指定间隔，使用默认间隔
    const interval = (intervalSeconds || state.config?.download_interval || 3) * 1000;
    console.log(`${interval}毫秒后执行下一步操作`);
    
    if (state.downloadTimer) {
        clearTimeout(state.downloadTimer);
    }
    
    state.downloadTimer = setTimeout(() => {
        if (state.isRunning) {
            action();
        }
    }, interval);
}

// 删除已处理的文件
function deleteProcessedFile() {
    if (!state.currentFile) {
        state.currentFile = null;
        automationLoop();
        return;
    }

    console.log(`删除已处理的文件: ${state.currentFile}`);
    setStatusMessage(`正在删除已处理的文件: ${state.currentFile}`);

    chrome.runtime.sendNativeMessage('com.cnki.downloader.bak', 
        { 
            action: 'deleteFile', 
            path: `${state.config.ndjson_dir}/${state.currentFile}` 
        }, 
        function(response) {
            if (chrome.runtime.lastError || !response || !response.success) {
                console.error('删除文件失败:', chrome.runtime.lastError || response?.error || '未知错误');
                setStatusMessage(`删除文件失败: ${chrome.runtime.lastError?.message || response?.error || '未知错误'}`);
            } else {
                console.log('文件删除成功');
                setStatusMessage(`文件 ${state.currentFile} 删除成功`);
            }

            // 无论删除是否成功，都继续循环
            state.currentFile = null;
            automationLoop();
        }
    );
}

//==============================================================================
// 消息监听和内容脚本注入
//==============================================================================

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

        sendResponse({
            isRunning: state.isRunning,
            isDownloading: state.isDownloading,
            currentIndex: state.currentDownloadIndex,
            totalCount: state.downloadQueue.length,
            remainingCount: state.downloadQueue.length - state.currentDownloadIndex,
            activeTabId: state.activeTabId,
            processingFile: state.currentFile,
            remainingFiles: state.filesToProcess.length,
            totalFiles: state.stats.totalFiles,
            completedFiles: state.stats.completedFiles,
            successFiles: state.stats.successFiles,
            failedFiles: state.stats.failedFiles,
            currentFile: state.stats.currentFile,
            statusMessage: state.statusMessage
        });

        return true; // 表示已处理
    }
});

// 设置内容脚本注入
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

// 初始化时检查是否有未完成的下载队列并加载配置
chrome.storage.local.get([
    'isRunning', 
    'isDownloading', 
    'downloadQueue', 
    'currentIndex', 
    'processingFiles', 
    'currentProcessingFile', 
    'downloadStats'
], function(data) {
    // 恢复下载统计
    if (data.downloadStats) {
        state.stats = data.downloadStats;
    }

    // 加载配置
    loadConfig();

    // 恢复自动化状态
    if (data.isRunning) {
        state.isRunning = false;
        stopAutomation();
    }
});
