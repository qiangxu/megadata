// popup.js - 修复版本，结合两种方法的优点
document.addEventListener('DOMContentLoaded', function() {
  // =====================================================
  // 1. 初始化变量和UI元素引用
  // =====================================================
  
  // 本地状态变量
  let paperLinks = {};     // 存储提取的论文信息
  
  // UI元素引用
  const ui = {
    extractBtn: document.getElementById('extractBtn'),
    copyAllBtn: document.getElementById('copyAllBtn'),
    downloadAllBtn: document.getElementById('downloadAllBtn'),
    sequentialBtn: document.getElementById('sequentialDownloadBtn'),
    stopBtn: document.getElementById('stopDownloadBtn'),
    intervalInput: document.getElementById('downloadInterval'),
    resultsDiv: document.getElementById('results'),
    statusDiv: document.getElementById('status'),
    progressDiv: document.getElementById('downloadProgress'),
    currentSpan: document.getElementById('currentDownload'),
    totalSpan: document.getElementById('totalDownload'),
    debugBtn: document.getElementById('debugBtn'),
    debugInfo: document.getElementById('debugInfo')
  };
  
  // 禁用相关按钮，直到提取到链接
  ui.copyAllBtn.disabled = true;
  ui.downloadAllBtn.disabled = true;
  ui.sequentialBtn.disabled = true;
  
  // =====================================================
  // 2. 辅助函数
  // =====================================================
  
  // 更新UI状态
  function updateUI(isLoading, message) {
    ui.statusDiv.textContent = message || '';
    
    if (isLoading) {
      // 加载中状态
      ui.extractBtn.disabled = true;
      ui.copyAllBtn.disabled = true;
      ui.downloadAllBtn.disabled = true;
      ui.sequentialBtn.disabled = true;
    } else {
      // 恢复状态
      ui.extractBtn.disabled = false;
      
      const hasLinks = Object.keys(paperLinks).length > 0;
      ui.copyAllBtn.disabled = !hasLinks;
      ui.downloadAllBtn.disabled = !hasLinks;
      ui.sequentialBtn.disabled = !hasLinks;
    }
  }
  
  // 更新下载进度显示
  function updateDownloadProgress(isDownloading, current, total) {
    ui.progressDiv.style.display = isDownloading ? 'block' : 'none';
    
    if (isDownloading) {
      ui.totalSpan.textContent = total;
      ui.currentSpan.textContent = current;
      ui.extractBtn.disabled = true;
      ui.copyAllBtn.disabled = true;
      ui.downloadAllBtn.disabled = true;
      ui.sequentialBtn.disabled = true;
    } else {
      ui.extractBtn.disabled = false;
      
      const hasLinks = Object.keys(paperLinks).length > 0;
      ui.copyAllBtn.disabled = !hasLinks;
      ui.downloadAllBtn.disabled = !hasLinks;
      ui.sequentialBtn.disabled = !hasLinks;
    }
  }
  
  // 模拟点击下载单个文件
  function simulateClick(url, title) {
    console.log(`准备下载: ${title}`);
    
    // 获取当前激活的标签页
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (!tabs || tabs.length === 0) {
        console.error('无法获取当前标签页');
        return;
      }
      
      const tabId = tabs[0].id;
      console.log(`向标签页 ${tabId} 发送模拟点击请求`);
      
      // 确保content script注入
      chrome.scripting.executeScript({
        target: { tabId: tabId },
        files: ['content.js']
      })
      .then(() => {
        // 发送模拟点击消息
        chrome.tabs.sendMessage(tabId, {
          action: "simulateClick",
          url: url,
          title: title
        }, function(response) {
          if (chrome.runtime.lastError) {
            console.error('发送消息失败:', chrome.runtime.lastError.message);
            return;
          }
          
          if (!response || !response.success) {
            console.error('模拟点击失败');
          } else {
            console.log('模拟点击成功');
          }
        });
      })
      .catch(error => {
        console.error('注入脚本失败:', error);
      });
    });
  }
  
  // =====================================================
  // 3. 主要功能实现
  // =====================================================
  
  // 提取链接
  function extractLinks() {
    updateUI(true, '正在提取链接...');
    ui.resultsDiv.innerHTML = '';
    
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (!tabs || tabs.length === 0) {
        updateUI(false, '无法获取当前标签页');
        return;
      }
      
      // 先确保注入content script
      chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
        files: ['content.js']
      }).then(() => {
        console.log('内容脚本已注入，发送提取请求');
        
        // 发送提取请求
        chrome.tabs.sendMessage(tabs[0].id, {action: "extract"}, function(response) {
          if (chrome.runtime.lastError) {
            updateUI(false, '提取失败: ' + chrome.runtime.lastError.message);
            return;
          }
          
          if (!response || !response.success) {
            updateUI(false, '提取失败: 未收到有效响应');
            return;
          }
          
          paperLinks = response.data;
          const count = Object.keys(paperLinks).length;
          
          if (count === 0) {
            updateUI(false, '未找到任何下载链接');
            return;
          }
          
          // 保存结果到存储
          chrome.storage.local.set({paperLinks: paperLinks});
          
          updateUI(false, `找到 ${count} 个下载链接`);
          displayLinks(paperLinks);
        });
      }).catch(error => {
        updateUI(false, '注入脚本失败: ' + error.message);
      });
    });
  }
  
  // 显示提取到的链接
  function displayLinks(links) {
    ui.resultsDiv.innerHTML = '';
    
    for (const title in links) {
      const paper = links[title];
      const paperDiv = document.createElement('div');
      paperDiv.className = 'paper';
      
      // 标题
      const titleDiv = document.createElement('div');
      titleDiv.className = 'paper-title';
      titleDiv.textContent = paper.title;
      paperDiv.appendChild(titleDiv);
      
      // 元数据
      if (paper.authors || paper.source || paper.date) {
        const metaDiv = document.createElement('div');
        metaDiv.className = 'paper-meta';
        let metaText = '';
        
        if (paper.authors) metaText += `作者: ${paper.authors} `;
        if (paper.source) metaText += `来源: ${paper.source} `;
        if (paper.date) metaText += `日期: ${paper.date}`;
        
        metaDiv.textContent = metaText.trim();
        paperDiv.appendChild(metaDiv);
      }
      
      // URL
      const urlDiv = document.createElement('div');
      urlDiv.className = 'paper-url';
      urlDiv.textContent = paper.url;
      paperDiv.appendChild(urlDiv);
      
      // 添加下载按钮
      const downloadBtn = document.createElement('button');
      downloadBtn.textContent = '下载';
      downloadBtn.addEventListener('click', function() {
        simulateClick(paper.url, paper.title);
      });
      paperDiv.appendChild(downloadBtn);
      
      // 添加复制链接按钮
      const copyBtn = document.createElement('button');
      copyBtn.textContent = '复制链接';
      copyBtn.addEventListener('click', function() {
        navigator.clipboard.writeText(paper.url)
          .then(() => {
            copyBtn.textContent = '已复制';
            setTimeout(() => copyBtn.textContent = '复制链接', 1500);
          })
          .catch(err => console.error('复制失败:', err));
      });
      paperDiv.appendChild(copyBtn);
      
      // 添加到结果区域
      ui.resultsDiv.appendChild(paperDiv);
    }
  }
  
  // 批量下载所有文件
  function downloadAll() {
    const papers = Object.values(paperLinks);
    if (papers.length === 0) return;
    
    papers.forEach(paper => {
      simulateClick(paper.url, paper.title);
    });
    
    updateUI(false, `已开始下载 ${papers.length} 个文件`);
  }
  
  // 开始顺序下载（发送请求到background.js）
  function startSequentialDownload() {
    console.log('请求开始顺序下载');
    
    const papers = Object.values(paperLinks);
    if (papers.length === 0) {
      updateUI(false, '没有可下载的链接');
      return;
    }
    
    // 获取下载间隔
    const interval = parseInt(ui.intervalInput.value, 10) || 3;
    console.log(`下载间隔设置为 ${interval} 秒`);
    
    // 获取当前标签页ID
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      if (!tabs || tabs.length === 0) {
        updateUI(false, '无法获取当前标签页');
        return;
      }
      
      const tabId = tabs[0].id;
      
      // 向background.js发送开始下载的请求
      chrome.runtime.sendMessage({
        action: "startSequentialDownload",
        downloadQueue: papers,
        interval: interval,
        tabId: tabId
      }, function(response) {
        if (chrome.runtime.lastError) {
          console.error('发送请求失败:', chrome.runtime.lastError);
          return;
        }
        
        if (response && response.success) {
          console.log('顺序下载已开始');
          
          // 更新UI显示下载正在进行
          updateDownloadProgress(true, 0, papers.length);
          updateUI(false, `开始顺序下载 ${papers.length} 个文件`);
        } else {
          console.error('开始下载请求失败');
          updateUI(false, '启动顺序下载失败');
        }
      });
    });
  }
  
  // 停止顺序下载
  function stopSequentialDownload() {
    console.log('请求停止顺序下载');
    
    chrome.runtime.sendMessage({
      action: "stopSequentialDownload"
    }, function(response) {
      if (chrome.runtime.lastError) {
        console.error('发送停止请求失败:', chrome.runtime.lastError);
        return;
      }
      
      if (response && response.success) {
        console.log('顺序下载已停止');
        updateDownloadProgress(false, 0, 0);
        updateUI(false, '下载已停止');
      } else {
        console.error('停止下载请求失败');
      }
    });
  }
  
  // 复制所有链接
  function copyAllLinks() {
    const links = Object.values(paperLinks).map(paper => paper.url).join('\n');
    
    navigator.clipboard.writeText(links)
      .then(() => updateUI(false, '已复制所有链接到剪贴板'))
      .catch(err => updateUI(false, '复制失败: ' + err));
  }
  
  // =====================================================
  // 4. 事件监听器和初始化
  // =====================================================
  
  // 提取按钮
  ui.extractBtn.addEventListener('click', extractLinks);
  
  // 一键下载所有按钮
  ui.downloadAllBtn.addEventListener('click', downloadAll);
  
  // 顺序下载按钮
  ui.sequentialBtn.addEventListener('click', startSequentialDownload);
  
  // 停止下载按钮
  ui.stopBtn.addEventListener('click', stopSequentialDownload);
  
  // 复制所有链接按钮
  ui.copyAllBtn.addEventListener('click', copyAllLinks);
  
  // 调试按钮
  if (ui.debugBtn) {
    ui.debugBtn.addEventListener('click', function() {
      // 获取当前下载状态
      chrome.runtime.sendMessage({ action: "getDownloadStatus" }, function(response) {
        const debug = {
          paperLinksCount: Object.keys(paperLinks).length,
          downloadStatus: response,
          interval: ui.intervalInput.value,
          buttonStates: {
            extract: ui.extractBtn.disabled,
            download: ui.downloadAllBtn.disabled,
            sequential: ui.sequentialBtn.disabled,
          }
        };
        
        if (ui.debugInfo) {
          ui.debugInfo.innerHTML = '<pre>' + JSON.stringify(debug, null, 2) + '</pre>';
        }
        console.log('当前状态:', debug);
      });
    });
  }
  
  // 初始化 - 检查当前下载状态
  function checkDownloadStatus() {
    chrome.runtime.sendMessage({ action: "getDownloadStatus" }, function(response) {
      if (chrome.runtime.lastError) {
        console.error('获取下载状态失败:', chrome.runtime.lastError);
        return;
      }
      
      console.log('当前下载状态:', response);
      
      if (response && response.isDownloading) {
        // 有正在进行的下载
        updateDownloadProgress(true, response.currentIndex, response.totalCount);
        updateUI(false, `下载中 (${response.currentIndex}/${response.totalCount})`);
      }
    });
  }
  
  // 恢复之前保存的链接数据
  chrome.storage.local.get(['paperLinks'], function(data) {
    if (data.paperLinks && Object.keys(data.paperLinks).length > 0) {
      paperLinks = data.paperLinks;
      displayLinks(paperLinks);
      updateUI(false, `找到 ${Object.keys(paperLinks).length} 个下载链接`);
    }
    
    // 检查是否有正在进行的下载
    checkDownloadStatus();
  });
  
  console.log('popup.js 初始化完成');
});
