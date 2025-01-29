/*
* CREATED DATE: Wed Jan 29 15:24:31 2025
* CREATED BY: qiangxu, toxuqiang@gmail.com
*/

// background.js
let urlPattern = 'https://mp.weixin.qq.com/cgi-bin/appmsgpublish'; // 默认匹配所有URL
let capturedUrls = [];

// 监听URL请求
chrome.webRequest.onBeforeRequest.addListener(
  (details) => {
    if (details.type === 'main_frame' || details.type === 'xmlhttprequest') {
      if (new RegExp(urlPattern).test(details.url)) {
        capturedUrls.push({
          url: details.url,
          timestamp: new Date().toISOString(),
          type: details.type
        });
        
        // 保存到 storage
        chrome.storage.local.set({ 'capturedUrls': capturedUrls });
      }
    }
  },
  { urls: ["<all_urls>"] }
);

// 监听来自popup的消息
chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
  if (request.action === 'getUrls') {
    sendResponse({ urls: capturedUrls });
  } else if (request.action === 'clearUrls') {
    capturedUrls = [];
    chrome.storage.local.set({ 'capturedUrls': [] });
    sendResponse({ success: true });
  } else if (request.action === 'setPattern') {
    urlPattern = request.pattern;
    chrome.storage.local.set({ 'urlPattern': urlPattern });
    sendResponse({ success: true });
  } else if (request.action === 'exportUrls') {
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `cap_fake_id_${timestamp}.json`;

	let filecontent = ''

	capturedUrls.forEach(u => {
      filecontent += `${u.url}\n`;
    });	
	const encodedUri = 'data:text/csv;charset=utf-8,\ufeff' + encodeURIComponent(filecontent);
    chrome.downloads.download({
      url: encodedUri,
      filename: filename,
    });

    sendResponse({ success: true });
  }
});


