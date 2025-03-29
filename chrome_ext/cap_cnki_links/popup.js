// popup.js
document.addEventListener('DOMContentLoaded', function() {
  const extractAndDownloadButton = document.getElementById('extractAndDownloadButton');
  const statusDiv = document.getElementById('status');
  
  // 加载域名配置文件
  function loadDomains() {
    return fetch(chrome.runtime.getURL('domains.txt'))
      .then(response => response.text())
      .then(text => {
        return text.split('\n')
          .map(line => line.trim())
          .filter(line => line !== '' && !line.startsWith('#'));
      })
      .catch(error => {
        console.error('加载域名配置文件失败:', error);
        // 默认域名列表
        return ['cnki.net', 'sjuku.top', '122.51.45.239', 'cnkionline.xyz'];
      });
  }
  
  // 检查当前页面，禁用/启用按钮
  chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
    const currentUrl = tabs[0].url;
    
    loadDomains().then(domains => {
      // 检查当前URL是否包含配置的任何域名
      const isMatchingDomain = domains.some(domain => currentUrl.includes(domain));
      
      if (isMatchingDomain) {
        extractAndDownloadButton.disabled = false;
        statusDiv.textContent = '点击按钮开始提取链接';
      } else {
        extractAndDownloadButton.disabled = true;
        statusDiv.textContent = '请在已配置的网站上使用此扩展';
      }
    });
  });
  
  // 提取链接并下载按钮点击事件
  extractAndDownloadButton.addEventListener('click', function() {
    statusDiv.textContent = '正在提取链接...';
    
    // 向当前标签页发送提取消息
    chrome.tabs.query({active: true, currentWindow: true}, function(tabs) {
      chrome.tabs.sendMessage(tabs[0].id, {action: "extract"}, function(response) {
        if (response && response.success) {
          const extractedData = response.data;
          const linkCount = Object.keys(extractedData).length;
          
          if (linkCount > 0) {
            statusDiv.textContent = `找到 ${linkCount} 个链接，正在保存...`;
            
            // 创建NDJSON格式
            let ndjsonContent = '';
            
            // 遍历提取的数据
            for (const title in extractedData) {
              const item = extractedData[title];
              // 确保每个字段都存在，如果不存在则使用空字符串
              const jsonItem = {
                title: item.title || title,
                url: item.url || '',
                authors: item.authors || '',
                source: item.source || '',
                date: item.date || ''
              };
              // 将每个对象转换为JSON字符串并添加换行符
              ndjsonContent += JSON.stringify(jsonItem) + '\n';
            }
            
            // 创建和下载文件
            const blob = new Blob([ndjsonContent], {type: 'application/x-json'});
            const url = URL.createObjectURL(blob);
            
            const date = new Date();
            const timestamp = `${date.getFullYear()}-${String(date.getMonth()+1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}-${String(date.getHours()).padStart(2, '0')}-${String(date.getMinutes()).padStart(2, '0')}-${String(date.getSeconds()).padStart(2, '0')}`;
            const filename = `cnki_${timestamp}.json`;
            
            chrome.downloads.download({
              url: url,
              filename: filename,
              saveAs: false
            }, function(downloadId) {
              if (chrome.runtime.lastError) {
                statusDiv.textContent = '下载失败: ' + chrome.runtime.lastError.message;
              } else {
                statusDiv.textContent = `已保存 ${linkCount} 个链接到 ${filename}`;
              }
            });
          } else {
            statusDiv.textContent = '未找到下载链接。可能是页面还没加载完成，请尝试刷新页面后重试。';
          }
        } else {
          statusDiv.textContent = '提取失败，请刷新页面后重试。如果问题持续，可能是页面结构与扩展不兼容。';
        }
      });
    });
  });
});
