//==============================================================================
// popup.js - 弹出窗口脚本，负责用户界面和交互
//==============================================================================

document.addEventListener('DOMContentLoaded', function() {
    // =====================================================
    // 1. 初始化变量和UI元素引用
    // =====================================================

    // 本地状态变量
    let paperLinks = {};     // 存储提取的论文信息
    let config = null;       // 存储配置
    let isRunning = false;   // 是否正在运行自动下载
    let downloadStats = {    // 下载统计信息
        total: 0,
        completed: 0,
        success: 0,
        failed: 0,
        currentFile: '', 
        currentUrl: ''  // 新增
    };



    // 更新UI元素引用 - 修改部分
    const ui = {
        startStopBtn: document.getElementById('startStopBtn'),
        clearBtn: document.getElementById('clearBtn'),
        totalFiles: document.getElementById('totalFiles'),
        completedFiles: document.getElementById('completedFiles'),
        successFiles: document.getElementById('successFiles'),
        failedFiles: document.getElementById('failedFiles'),
        progressBar: document.getElementById('progressBar'),
        currentFileInfo: document.getElementById('currentFileInfo'),
        currentFileName: document.getElementById('currentFileName'),
        currentDownloadUrl: document.getElementById('currentDownloadUrl'), // 新增
        configInfoDiv: document.getElementById('configInfo'),
        statusDiv: document.getElementById('status'),
        resultsDiv: document.getElementById('results')
    };

    // 在popup.js中添加一个诊断按钮
    const diagnosticBtn = document.createElement('button');
    diagnosticBtn.textContent = '诊断下载问题';
    diagnosticBtn.className = 'diagnostic-btn';
    diagnosticBtn.addEventListener('click', checkTabStatus);
    document.querySelector('.main-controls').appendChild(diagnosticBtn);

    // 在popup.js中添加测试按钮
    const testDownloadBtn = document.createElement('button');
    testDownloadBtn.textContent = '测试下载';
    testDownloadBtn.addEventListener('click', function() {
        // 获取当前一个URL进行测试
        const testUrl = "这里填入一个有效的下载链接";

        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            if (!tabs || tabs.length === 0) {
                console.error('无法获取当前标签页');
                return;
            }

            chrome.tabs.sendMessage(tabs[0].id, {
                action: "simulateClick",
                url: testUrl,
                title: "测试下载"
            });
        });
    });

    document.querySelector('.main-controls').appendChild(testDownloadBtn);
    // =====================================================
    // 2. 配置文件加载
    // =====================================================


    // 加载配置文件
    function loadConfig() {
        fetch(chrome.runtime.getURL('config.yaml'))
            .then(response => {
                if (!response.ok) {
                    throw new Error(`无法加载配置文件: ${response.status}`);
                }
                return response.text();
            })
            .then(yamlText => {
                try {
                    // 使用js-yaml解析YAML
                    config = jsyaml.load(yamlText);
                    console.log('成功加载配置:', config);

                    // 更新UI显示配置信息
                    updateConfigInfo();
                } catch (e) {
                    console.error('解析配置文件时出错:', e);
                    ui.configInfoDiv.innerHTML = `<div class="error">配置文件解析失败: ${e.message}</div>`;
                }
            })
            .catch(error => {
                console.error('加载配置文件失败:', error);
                ui.configInfoDiv.innerHTML = `<div class="error">加载配置文件失败: ${error.message}</div>`;
            });
    }

    // 更新配置信息显示
    function updateConfigInfo() {
        if (!config) {
            ui.configInfoDiv.innerHTML = '<div class="warning">未加载配置</div>';
            return;
        }

        ui.configInfoDiv.innerHTML = `
      <div class="config-summary">
        <h3>配置信息</h3>
        <div><strong>NDJSON目录:</strong> ${config.ndjson_dir}</div>
        <div><strong>下载间隔:</strong> ${config.download_interval} 秒</div>
        <div><strong>下载后删除:</strong> ${config.delete_after_download ? '是' : '否'}</div>
        ${config.download_path ? `<div><strong>下载路径:</strong> ${config.download_path}</div>` : ''}
        ${config.filename_prefix ? `<div><strong>文件名前缀:</strong> ${config.filename_prefix}</div>` : ''}
      </div>
    `;
    }

    // =====================================================
    // 3. 主要功能实现
    // =====================================================

    // 切换开始/停止状态
    function toggleStartStop() {
        if (isRunning) {
            // 当前正在运行，需要停止
            stopAutomation();
        } else {
            // 当前已停止，需要开始
            startAutomation();
        }
    }

    // 开始自动下载流程
    function startAutomation() {
        if (!config) {
            updateStatus('配置未加载，无法启动');
            return;
        }

        updateStatus('正在启动自动下载流程...');

        // 向background.js发送开始处理的消息
        chrome.runtime.sendMessage({
            action: "startAutomation"
        }, function(response) {
            if (chrome.runtime.lastError) {
                console.error('发送启动请求失败:', chrome.runtime.lastError);
                updateStatus('启动失败: ' + chrome.runtime.lastError.message);
                return;
            }

            if (response && response.success) {
                isRunning = true;
                updateStartStopButton();
                updateStatus('自动下载已启动');

                // 开始定期查询状态
                startStatusPolling();
            } else {
                updateStatus('启动失败: ' + (response?.error || '未知错误'));
            }
        });
    }

    // 停止自动下载流程
    function stopAutomation() {
        updateStatus('正在停止自动下载流程...');

        // 向background.js发送停止处理的消息
        chrome.runtime.sendMessage({
            action: "stopAutomation"
        }, function(response) {
            if (chrome.runtime.lastError) {
                console.error('发送停止请求失败:', chrome.runtime.lastError);
                updateStatus('停止失败: ' + chrome.runtime.lastError.message);
                return;
            }

            if (response && response.success) {
                isRunning = false;
                updateStartStopButton();
                updateStatus('自动下载已停止');

                // 停止状态轮询
                stopStatusPolling();
            } else {
                updateStatus('停止失败: ' + (response?.error || '未知错误'));
            }
        });
    }

    // 清空所有数据
    function clearAllData() {
        if (isRunning) {
            if (!confirm('当前正在运行自动下载，确定要清空所有数据吗？这将停止当前的下载任务。')) {
                return;
            }
            stopAutomation();
        } else if (!confirm('确定要清空所有数据吗？这将删除所有的下载记录和状态。')) {
            return;
        }

        // 重置本地状态
        paperLinks = {};
        downloadStats = {
            total: 0,
            completed: 0,
            success: 0,
            failed: 0,
            currentFile: ''
        };

        // 更新UI
        updateDownloadStats();
        ui.resultsDiv.innerHTML = '';

        // 向background.js发送清空数据的消息
        chrome.runtime.sendMessage({
            action: "clearAllData"
        }, function(response) {
            if (chrome.runtime.lastError) {
                console.error('发送清空请求失败:', chrome.runtime.lastError);
                updateStatus('清空数据失败: ' + chrome.runtime.lastError.message);
                return;
            }

            if (response && response.success) {
                updateStatus('所有数据已清空');
            } else {
                updateStatus('清空数据失败: ' + (response?.error || '未知错误'));
            }
        });
    }


    // 更新下载统计信息 - 修改此函数
    function updateDownloadStats() {
        ui.totalFiles.textContent = downloadStats.total;
        ui.completedFiles.textContent = downloadStats.completed;
        ui.successFiles.textContent = downloadStats.success;
        ui.failedFiles.textContent = downloadStats.failed;

        // 更新进度条
        const percentage = downloadStats.total > 0 ? 
            (downloadStats.completed / downloadStats.total * 100) : 0;
        ui.progressBar.style.width = `${percentage}%`;

        // 更新当前文件信息
        if (downloadStats.currentFile) {
            ui.currentFileInfo.style.display = 'block';
            ui.currentFileName.textContent = downloadStats.currentFile;

            // 更新当前下载URL
            if (downloadStats.currentUrl) {
                ui.currentDownloadUrl.textContent = downloadStats.currentUrl;
            } else {
                ui.currentDownloadUrl.textContent = '-';
            }
        } else {
            ui.currentFileInfo.style.display = 'none';
        }
    }

    // 更新开始/停止按钮状态
    function updateStartStopButton() {
        if (isRunning) {
            ui.startStopBtn.textContent = '停止自动下载';
            ui.startStopBtn.classList.remove('start');
            ui.startStopBtn.classList.add('stop');
        } else {
            ui.startStopBtn.textContent = '开始自动下载';
            ui.startStopBtn.classList.remove('stop');
            ui.startStopBtn.classList.add('start');
        }
    }

    // 更新状态信息
    function updateStatus(message) {
        ui.statusDiv.textContent = message;
    }

    // 轮询状态的定时器
    let statusPollingInterval = null;

    // 开始定期查询状态
    function startStatusPolling() {
        // 清除可能存在的旧定时器
        stopStatusPolling();

        // 立即查询一次
        fetchDownloadStatus();

        // 设置新的轮询定时器
        statusPollingInterval = setInterval(fetchDownloadStatus, 1000);
    }

    // 停止状态轮询
    function stopStatusPolling() {
        if (statusPollingInterval) {
            clearInterval(statusPollingInterval);
            statusPollingInterval = null;
        }
    }

    // 获取当前下载状态

    function fetchDownloadStatus() {
        chrome.runtime.sendMessage({
            action: "getDownloadStatus"
        }, function(response) {
            if (chrome.runtime.lastError) {
                console.error('获取状态失败:', chrome.runtime.lastError);
                return;
            }

            if (response) {
                // 更新运行状态
                isRunning = response.isRunning;
                updateStartStopButton();

                // 更新下载统计
                downloadStats = {
                    total: response.totalFiles || 0,
                    completed: response.completedFiles || 0,
                    success: response.successFiles || 0,
                    failed: response.failedFiles || 0,
                    currentFile: response.currentFile || '',
                    currentUrl: response.currentUrl || ''  // 新增
                };
                updateDownloadStats();

                // 更新状态消息
                if (response.statusMessage) {
                    updateStatus(response.statusMessage);
                }
            }
        });
    }

    // 添加一个诊断函数，查看当前标签页状态
    function checkTabStatus() {
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            if (!tabs || tabs.length === 0) {
                console.error('无法获取当前标签页');
                updateStatus('诊断: 无法获取当前标签页');
                return;
            }

            const tab = tabs[0];
            console.log('当前活动标签页:', tab);
            updateStatus(`诊断: 当前标签页 ${tab.id}, URL: ${tab.url.substring(0, 30)}...`);

            // 检查content script是否已注入
            chrome.tabs.sendMessage(tab.id, {action: "ping"}, function(response) {
                if (chrome.runtime.lastError) {
                    console.error('Content script未注入:', chrome.runtime.lastError);
                    updateStatus('诊断: Content Script未注入到当前标签页');
                } else if (response && response.pong) {
                    console.log('Content script已注入');
                    updateStatus('诊断: Content Script已正确注入');
                }
            });
        });
    }


    // =====================================================
    // 4. 事件监听器和初始化
    // =====================================================

    // 开始/停止按钮
    if (ui.startStopBtn) {
        ui.startStopBtn.addEventListener('click', toggleStartStop);
    }

    // 清空数据按钮
    if (ui.clearBtn) {
        ui.clearBtn.addEventListener('click', clearAllData);
    }

    // 加载js-yaml库
    function loadJsYaml() {
        return new Promise((resolve, reject) => {
            if (window.jsyaml) {
                resolve();
                return;
            }

            const script = document.createElement('script');
            script.src = chrome.runtime.getURL('js-yaml.min.js');
            script.onload = resolve;
            script.onerror = reject;
            document.head.appendChild(script);
        });
    }

    // 初始化
    async function initialize() {
        try {
            // 加载js-yaml库
            await loadJsYaml();

            // 加载配置
            loadConfig();

            // 获取当前状态
            fetchDownloadStatus();

            // 如果自动下载正在运行，开始状态轮询
            chrome.runtime.sendMessage({ action: "getDownloadStatus" }, function(response) {
                if (response && response.isRunning) {
                    isRunning = true;
                    updateStartStopButton();
                    startStatusPolling();
                }
            });
        } catch (error) {
            console.error('初始化失败:', error);
            updateStatus('初始化失败: ' + error.message);
        }
    }

    // 在 popup.js 中添加
    function testContentScript() {
        chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
            if (!tabs || tabs.length === 0) {
                console.error('无法获取当前标签页');
                return;
            }

            const tabId = tabs[0].id;
            console.log('测试与标签页 ' + tabId + ' 的通信');

            chrome.tabs.sendMessage(tabId, { action: "ping" }, function(response) {
                if (chrome.runtime.lastError) {
                    console.error('通信失败:', chrome.runtime.lastError);
                    alert('Content script 未正确加载: ' + chrome.runtime.lastError.message);
                } else if (response && response.pong) {
                    console.log('通信成功');
                    alert('Content script 已正确加载并响应!');
                } else {
                    console.error('收到意外响应');
                    alert('收到意外响应: ' + JSON.stringify(response));
                }
            });
        });
    }
    // 开始初始化
    initialize();

    console.log('popup.js 初始化完成');
    // 添加测试按钮
    const testCsBtn = document.createElement('button');
    testCsBtn.textContent = '测试 Content Script';
    testCsBtn.addEventListener('click', testContentScript);
    document.querySelector('.main-controls').appendChild(testCsBtn);
});


