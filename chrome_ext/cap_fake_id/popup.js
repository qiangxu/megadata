/*
* CREATED DATE: Wed Jan 29 15:25:17 2025
* CREATED BY: qiangxu, toxuqiang@gmail.com
*/

document.addEventListener('DOMContentLoaded', () => {
  // 加载已保存的URL pattern
  chrome.storage.local.get('urlPattern', (data) => {
    if (data.urlPattern) {
      document.getElementById('patternInput').value = data.urlPattern;
    }
  });

  // 更新URL列表
  function updateUrlList() {
    chrome.runtime.sendMessage({ action: 'getUrls' }, (response) => {
      const urlList = document.getElementById('urlList');
      urlList.innerHTML = '';
      
      response.urls.forEach(item => {
        const div = document.createElement('div');
        div.className = 'url-item';
        div.textContent = `[${item.timestamp}] ${item.url}`;
        urlList.appendChild(div);
      });
    });
  }

  // 初始加载URL列表
  updateUrlList();

  // 设置URL pattern
  document.getElementById('setPattern').addEventListener('click', () => {
    const pattern = document.getElementById('patternInput').value;
    chrome.runtime.sendMessage({ 
      action: 'setPattern', 
      pattern: pattern 
    }, () => {
      alert('URL PATTERN已更新');
    });
  });

  // 导出URLs
  document.getElementById('exportBtn').addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'exportUrls' });
  });

  // 清除记录
  document.getElementById('clearBtn').addEventListener('click', () => {
    chrome.runtime.sendMessage({ action: 'clearUrls' }, () => {
      updateUrlList();
      alert('记录已清除');
    });
  });
});
