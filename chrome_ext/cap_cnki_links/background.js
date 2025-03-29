// background.js
// 后台脚本，负责处理扩展的后台任务

// 扩展安装时的初始化
chrome.runtime.onInstalled.addListener(() => {
  console.log('知网下载链接提取器已安装');
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
            }).catch(error => console.error(`内容脚本注入失败: ${error}`));
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

// 启动时加载域名配置
loadDomainsAndSetupListeners();
