// background.js - 管理下载队列但通过content.js执行实际点击

// 全局状态变量
let downloadQueue = [];
let currentIndex = 0;
let isDownloading = false;
let downloadTimer = null;
let activeTabId = null;

// 扩展安装或更新时初始化
chrome.runtime.onInstalled.addListener(() => {
  console.log('知网下载链接提取器已安装/更新');
  
  // 初始化存储默认设置
  chrome.storage.local.set({
    downloadInterval: 3,  // 默认下载间隔为3秒
    isDownloading: false,
    downloadQueue: [],
    currentIndex: 0,
    paperLinks: {}
  });
});

// 加载域名配置文件并监听这些域名上的页面完成加载事件
function loadDomainsAndSetupListeners() {
  fetch(chrome.runtime.getURL('domains.txt'))
    .then(response => response.text())
    .then(text => {
      const domains = text.split('\n')
        .map(line => line.trim())
        .filter(line => line !== '' && !line.startsWith('#'));
      
      // 对每个配置的域名，设置webNavigation监听器
      domains.forEach(domain => {
        chrome.webNavigation.onCompleted.addListener(
          function(details) {
            // 页面加载完成后注入content script
            chrome.scripting.executeScript({
              target: { tabId: details.tabId },
              files: ['content.js']
            })
            .then(() => {
              console.log(`内容脚本成功注入到标签页 ${details.tabId}`);
            })
            .catch(error => console.error(`内容脚本注入失败: ${error}`));
          }, 
          { url: [{ hostContains: domain }] }
        );
      });
    })
    .catch(error => {
      console.error('加载域名配置文件失败:', error);
      // 使用默认域名
      const defaultDomains = ['cnki.net', 'sjuku.top', '122.51.45.239', 'cnkionline.xyz'];
      defaultDomains.forEach(domain => {
        chrome.webNavigation.onCompleted.addListener(
          function(details) {
            chrome.scripting.executeScript({
              target: { tabId: details.tabId },
              files: ['content.js']
            }).catch(error => console.error(`内容脚本注入失败: ${error}`));
          }, 
          { url: [{ hostContains: domain }] }
        );
      });
    });
}

// 监听来自popup的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  // 处理各种请求
  if (request.action === "startSequentialDownload") {
    console.log("收到开始顺序下载请求", request);
    
    // 保存活跃标签页ID
    activeTabId = request.tabId;
    
    // 保存下载信息
    downloadQueue = request.downloadQueue;
    currentIndex = 0;
    isDownloading = true;
    
    // 更新存储状态
    chrome.storage.local.set({
      downloadQueue: downloadQueue,
      currentIndex: currentIndex,
      isDownloading: isDownloading,
      downloadInterval: request.interval,
      activeTabId: activeTabId
    }, () => {
      console.log("存储状态已更新，开始顺序下载");
      
      // 开始顺序下载
      processNextDownload(request.interval || 3);
      sendResponse({success: true});
    });
    
    return true; // 表示将异步返回response
  } 
  else if (request.action === "stopSequentialDownload") {
    console.log("收到停止顺序下载请求");
    
    if (downloadTimer) {
      clearTimeout(downloadTimer);
      downloadTimer = null;
    }
    
    isDownloading = false;
    downloadQueue = [];
    
    // 更新存储
    chrome.storage.local.set({
      isDownloading: false,
      downloadQueue: [],
      currentIndex: 0,
      activeTabId: null
    }, () => {
      console.log("已停止顺序下载，存储状态已更新");
      sendResponse({success: true});
    });
    
    return true; // 表示将异步返回response
  } 
  else if (request.action === "getDownloadStatus") {
    console.log("收到获取下载状态请求");
    
    sendResponse({
      isDownloading: isDownloading,
      currentIndex: currentIndex,
      totalCount: downloadQueue.length,
      remainingCount: downloadQueue.length - currentIndex,
      activeTabId: activeTabId
    });
    
    return true; // 表示已处理
  }
  else if (request.action === "simulateClickDone") {
    // 接收来自content.js的点击完成通知
    console.log("收到点击完成通知", request);
    sendResponse({success: true});
    return true;
  }
});

// 处理下一个下载
function processNextDownload(intervalSeconds) {
  console.log(`处理下载队列: 当前索引=${currentIndex}, 总数=${downloadQueue.length}`);
  
  // 检查是否已完成或停止
  if (!isDownloading || downloadQueue.length === 0 || currentIndex >= downloadQueue.length) {
    console.log('下载队列已完成或停止');
    isDownloading = false;
    
    // 更新存储
    chrome.storage.local.set({
      isDownloading: false,
      downloadQueue: [],
      currentIndex: 0,
      activeTabId: null
    });
    
    return;
  }
  
  // 获取当前下载项
  const paper = downloadQueue[currentIndex];
  console.log(`正在下载: ${paper.title}`);
  
  // 检查标签页是否还存在
  chrome.tabs.get(activeTabId, tab => {
    if (chrome.runtime.lastError || !tab) {
      console.log('原始标签页已关闭，尝试找到或创建新标签页');
      
      // 尝试找到知网相关标签页
      chrome.tabs.query({}, tabs => {
        let knownTabFound = false;
        
        for (const tab of tabs) {
          if (tab.url && (
            tab.url.includes('cnki.net') ||
            tab.url.includes('sjuku.top') ||
            tab.url.includes('cnkionline.xyz') ||
            tab.url.includes('知网')
          )) {
            activeTabId = tab.id;
            knownTabFound = true;
            
            // 更新存储
            chrome.storage.local.set({activeTabId: activeTabId});
            
            // 确保content script已注入
            chrome.scripting.executeScript({
              target: { tabId: activeTabId },
              files: ['content.js']
            })
            .then(() => {
              // 发送模拟点击请求到content script
              sendSimulateClickMessage(activeTabId, paper);
            })
            .catch(error => {
              console.error('注入脚本失败:', error);
              moveToNextDownload(intervalSeconds);
            });
            
            break;
          }
        }
        
        // 如果没有找到合适的标签页，创建一个新标签页
        if (!knownTabFound) {
          chrome.tabs.create({ url: 'https://www.cnki.net', active: false }, newTab => {
            activeTabId = newTab.id;
            chrome.storage.local.set({activeTabId: activeTabId});
            
            // 等待页面加载完成
            setTimeout(() => {
              chrome.scripting.executeScript({
                target: { tabId: activeTabId },
                files: ['content.js']
              })
              .then(() => {
                sendSimulateClickMessage(activeTabId, paper);
              })
              .catch(error => {
                console.error('注入脚本失败:', error);
                moveToNextDownload(intervalSeconds);
              });
            }, 2000);
          });
        }
      });
    } else {
      // 原始标签页仍然存在，直接发送消息
      sendSimulateClickMessage(activeTabId, paper);
    }
  });
}

// 发送模拟点击消息到content script
function sendSimulateClickMessage(tabId, paper) {
  console.log(`向标签页 ${tabId} 发送模拟点击请求`);
  
  chrome.tabs.sendMessage(tabId, {
    action: "simulateClick",
    url: paper.url,
    title: paper.title
  }, response => {
    // 无论成功与否，都移动到下一个下载
    if (chrome.runtime.lastError) {
      console.error('发送消息失败:', chrome.runtime.lastError.message);
    } else if (!response || !response.success) {
      console.error('模拟点击失败');
    } else {
      console.log('模拟点击成功');
    }
    
    // 获取下载间隔
    chrome.storage.local.get(['downloadInterval'], data => {
      const interval = data.downloadInterval || 3;
      moveToNextDownload(interval);
    });
  });
}

// 移动到下一个下载项
function moveToNextDownload(intervalSeconds) {
  // 更新索引
  currentIndex++;
  chrome.storage.local.set({ currentIndex: currentIndex });
  
  // 设置定时器处理下一个
  const intervalMs = intervalSeconds * 1000;
  console.log(`${intervalMs}毫秒后下载下一个`);
  
  downloadTimer = setTimeout(() => {
    processNextDownload(intervalSeconds);
  }, intervalMs);
}

// 初始化时检查是否有未完成的下载队列
chrome.storage.local.get(['isDownloading', 'downloadQueue', 'currentIndex', 'downloadInterval', 'activeTabId'], 
  function(data) {
    if (data.isDownloading && data.downloadQueue && data.downloadQueue.length > 0) {
      console.log('发现未完成的下载队列，恢复下载');
      
      downloadQueue = data.downloadQueue;
      currentIndex = data.currentIndex || 0;
      isDownloading = true;
      activeTabId = data.activeTabId;
      
      // 恢复下载
      processNextDownload(data.downloadInterval || 3);
    }
  }
);

// 启动时加载域名配置
loadDomainsAndSetupListeners();
