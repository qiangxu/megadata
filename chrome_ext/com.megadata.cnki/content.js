//==============================================================================
// content.js - 内容脚本，负责模拟点击下载链接
//==============================================================================
// 防止重复初始化
if (window.cnkiExtractorInitialized) {
	console.log('[知网下载链接提取器] 脚本已初始化，跳过重复加载');
} else {
	// 设置全局标志
	window.cnkiExtractorInitialized = true;
	// 监听消息
	chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
		console.log('[知网下载链接提取器] 收到消息:', request);

		if (request.action === "ping") {
			console.log('[知网下载链接提取器] 收到ping请求');
			sendResponse({ pong: true });
			return true;
		}

		if (request.action === "simulateClick") {
			console.log('[知网下载链接提取器] 收到点击请求:', request.url);

			try {
				// 创建临时链接并点击
				const a = document.createElement('a');
				a.href = request.url;
				a.target = '_blank';
				a.style.display = 'none';
				document.body.appendChild(a);
				console.log('[知网下载链接提取器] 创建链接元素:', a);

				// 点击
				a.click();
				console.log('[知网下载链接提取器] 已执行点击');

				// 清理
				setTimeout(() => {
					document.body.removeChild(a);
					console.log('[知网下载链接提取器] 已移除临时元素');
				}, 100);

				sendResponse({ success: true });
			} catch (error) {
				console.error('[知网下载链接提取器] 点击操作失败:', error);
				sendResponse({ success: false, error: error.message });
			}

			return true;
		}
	});

	console.log('[知网下载链接提取器] 简化版脚本加载完成'); 
}



