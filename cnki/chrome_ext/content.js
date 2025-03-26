// content.js
// 此脚本将注入到知网页面，用于提取下载链接和论文名称
(function() {
  // 默认的链接模式，当配置文件无法加载时使用
  let linkPatterns = [
    '/download.php',
    'api1.sjuku.top',
    '/downpaper',
    '/bar/download/order'
  ];
  
  // 尝试加载链接模式配置文件
  function loadLinkPatterns() {
    return new Promise((resolve) => {
      // 使用chrome.runtime.getURL获取配置文件的完整URL
      fetch(chrome.runtime.getURL('links.txt'))
        .then(response => {
          if (!response.ok) {
            throw new Error(`HTTP error! Status: ${response.status}`);
          }
          return response.text();
        })
        .then(text => {
          // 按行分割文本，过滤空行和注释行
          const lines = text.split('\n')
                         .map(line => line.trim())
                         .filter(line => line !== '' && !line.startsWith('#'));
          if (lines.length > 0) {
            linkPatterns = lines;
            console.log('[知网下载链接提取器] 链接模式配置文件加载成功，共加载 ' + lines.length + ' 个模式', linkPatterns);
          }
          resolve();
        })
        .catch(error => {
          console.error('[知网下载链接提取器] 加载链接模式配置文件失败:', error);
          console.log('[知网下载链接提取器] 使用默认链接模式:', linkPatterns);
          resolve(); // 即使失败也继续使用默认模式
        });
    });
  }

  // 检查链接是否匹配配置的链接模式
  function isMatchingLink(url) {
    if (!url) return false;
    
    for (const pattern of linkPatterns) {
      if (url.includes(pattern)) {
        console.log(`[知网下载链接提取器] 匹配到链接模式 "${pattern}": ${url}`);
        return true;
      }
    }
    return false;
  }

  // 监听来自popup的消息
  chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    if (request.action === "extract") {
      console.log('[知网下载链接提取器] 收到提取请求');
      // 先加载配置，然后提取链接
      loadLinkPatterns().then(() => {
        const paperLinks = extractPaperLinks();
        const linkCount = Object.keys(paperLinks).length;
        console.log(`[知网下载链接提取器] 提取完成，共找到 ${linkCount} 个链接`);
        sendResponse({success: true, data: paperLinks});
      });
      return true; // 表示将异步返回response
    }
  });

  // 提取页面上的下载链接和论文名称
  function extractPaperLinks() {
    const result = {};
    
    console.log('[知网下载链接提取器] 开始提取链接...');
    
    // 查找所有表格行
    const rows = document.querySelectorAll('tr');
    console.log(`[知网下载链接提取器] 找到 ${rows.length} 个表格行`);
    
    rows.forEach((row, index) => {
      // 查找论文标题 - 支持多种可能的类名
      const titleElement = row.querySelector('.wz_tab, .fz14');
      if (!titleElement) {
        console.log(`[知网下载链接提取器] 行 #${index+1} 没有找到标题元素`);
        return;
      }
      
      // 获取标题文本，考虑可能的子元素
      let title = '';
      if (titleElement.innerText) {
        title = titleElement.innerText.trim();
      } else if (titleElement.querySelector('font')) {
        // 处理如 <a class="fz14"><font color="red">标题</font></a> 的情况
        title = titleElement.querySelector('font').innerText.trim();
      }
      
      if (!title) {
        console.log(`[知网下载链接提取器] 行 #${index+1} 没有找到有效标题文本`);
        return;
      }
      
      console.log(`[知网下载链接提取器] 行 #${index+1} 找到标题: "${title}"`);
      
      // 创建结果对象
      const paperInfo = {
        title: title,
        url: "",
        authors: "",
        source: "",
        date: ""
      };
      
      // 查找作者信息
      const authorCell = row.querySelector('td.author');
      if (authorCell) {
        paperInfo.authors = authorCell.innerText.trim();
        console.log(`[知网下载链接提取器] 行 #${index+1} 作者: ${paperInfo.authors}`);
      }
      
      // 查找来源信息
      const sourceCell = row.querySelector('td.source');
      if (sourceCell) {
        paperInfo.source = sourceCell.innerText.trim();
        console.log(`[知网下载链接提取器] 行 #${index+1} 来源: ${paperInfo.source}`);
      }
      
      // 查找日期信息
      const dateCell = row.querySelector('td.date');
      if (dateCell) {
        paperInfo.date = dateCell.innerText.trim();
        console.log(`[知网下载链接提取器] 行 #${index+1} 日期: ${paperInfo.date}`);
      }
      
      // 提取标题行中的URL
      const titleLink = titleElement.getAttribute('href');
      if (titleLink && isMatchingLink(titleLink)) {
        console.log(`[知网下载链接提取器] 行 #${index+1} 标题链接匹配下载模式`);
        paperInfo.url = titleLink;
        result[title] = paperInfo;
        return; // 如果已找到标题链接则返回
      }
      
      // 首先尝试查找具有特定类的下载链接
      const specificDownloadLinks = row.querySelectorAll('.downloadlink, .icon-notlogged, a[title*="下载"]');
      console.log(`[知网下载链接提取器] 行 #${index+1} 找到 ${specificDownloadLinks.length} 个特定下载链接`);
      
      if (specificDownloadLinks.length > 0) {
        for (const link of specificDownloadLinks) {
          const href = link.getAttribute('href') || '';
          if (href) {
            console.log(`[知网下载链接提取器] 行 #${index+1} 使用特定下载链接: ${href}`);
            paperInfo.url = href;
            result[title] = paperInfo;
            return;  // 找到特定下载链接就直接返回
          }
        }
      }
      
      // 如果没有找到特定类的下载链接，则查找所有链接
      const allLinks = row.querySelectorAll('a');
      console.log(`[知网下载链接提取器] 行 #${index+1} 查找所有链接: ${allLinks.length} 个`);
      
      for (const link of allLinks) {
        const href = link.getAttribute('href') || '';
        const onclick = link.getAttribute('onclick') || '';
        const linkTitle = link.getAttribute('title') || '';
        const linkText = link.textContent || '';
        
        // 检查href是否包含下载链接
        if (isMatchingLink(href)) {
          console.log(`[知网下载链接提取器] 行 #${index+1} 链接href匹配下载模式: ${href}`);
          paperInfo.url = href;
          result[title] = paperInfo;
          break;
        }
        
        // 检查链接文本或标题是否包含"下载"关键词
        if ((linkTitle.includes('下载') || linkText.includes('下载')) && href) {
          console.log(`[知网下载链接提取器] 行 #${index+1} 链接文本包含"下载": ${href}`);
          paperInfo.url = href;
          result[title] = paperInfo;
          break;
        }
        
        // 检查onclick是否包含下载链接
        if (onclick) {
          const urlMatch = onclick.match(/(https?:\/\/[^'"]+)/);
          if (urlMatch && isMatchingLink(urlMatch[1])) {
            console.log(`[知网下载链接提取器] 行 #${index+1} onclick属性匹配下载模式: ${urlMatch[1]}`);
            paperInfo.url = urlMatch[1];
            result[title] = paperInfo;
            break;
          }
        }
      }
      
      // 检查是否已找到该标题的下载链接
      if (result[title] && result[title].url) {
        console.log(`[知网下载链接提取器] 行 #${index+1} 成功找到下载链接`);
      } else {
        console.log(`[知网下载链接提取器] 行 #${index+1} 未找到下载链接`);
      }
    });
    
    // 查找所有脚本内包含的下载链接
    extractFromScripts(result);
    
    return result;
  }
  
  // 从脚本中提取下载链接和标题信息
  function extractFromScripts(result) {
    console.log('[知网下载链接提取器] 开始从脚本中提取链接...');
    
    const scripts = document.querySelectorAll('script');
    console.log(`[知网下载链接提取器] 找到 ${scripts.length} 个脚本标签`);
    
    let scriptLinksFound = 0;
    
    scripts.forEach((script, index) => {
      const content = script.textContent || '';
      if (!content) return;
      
      // 为每个链接模式创建动态正则表达式
      linkPatterns.forEach(pattern => {
        // 转义特殊字符
        const escapedPattern = pattern.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const regex = new RegExp(`(https?://[^"']+${escapedPattern}[^"']+)`, 'g');
        
        let match;
        while ((match = regex.exec(content)) !== null) {
          scriptLinksFound++;
          console.log(`[知网下载链接提取器] 脚本 #${index+1} 匹配到链接: ${match[1]}`);
          
          // 尝试从URL中的参数提取标题信息
          if (match[1].includes('ddata=')) {
            const ddataMatch = match[1].match(/ddata=([^&]+)/);
            if (ddataMatch) {
              try {
                const ddataValue = decodeURIComponent(ddataMatch[1]);
                const parts = ddataValue.split('|');
                if (parts.length > 2) {
                  // ddata第三个部分通常是标题
                  const title = decodeURIComponent(parts[2]);
                  if (title && !result[title]) {
                    console.log(`[知网下载链接提取器] 从URL参数提取到标题: "${title}"`);
                    // 如果从脚本中提取，可能缺少作者、来源和日期信息
                    result[title] = {
                      title: title,
                      url: match[1],
                      authors: "", // 从URL参数中提取不到作者信息
                      source: "", // 从URL参数中提取不到来源信息
                      date: ""    // 从URL参数中提取不到日期信息
                    };
                    
                    // 尝试从ddata中解析更多信息
                    if (parts.length > 4) {
                      result[title].source = decodeURIComponent(parts[4]);
                    }
                    if (parts.length > 5) {
                      result[title].date = decodeURIComponent(parts[5]);
                    }
                  }
                }
              } catch (e) {
                // 忽略解码错误
                console.error("[知网下载链接提取器] 解析URL参数出错:", e);
              }
            }
          }
        }
      });
    });
    
    console.log(`[知网下载链接提取器] 脚本中共找到 ${scriptLinksFound} 个链接`);
    
    // 尝试从页面标题元素中提取
    const mainTitle = document.querySelector('h1, .main-title, .title');
    if (mainTitle) {
      const title = mainTitle.innerText.trim();
      console.log(`[知网下载链接提取器] 页面主标题: "${title}"`);
      
      // 寻找页面中所有可能的下载链接
      document.querySelectorAll('a').forEach(link => {
        const href = link.getAttribute('href') || '';
        if (isMatchingLink(href) && title && !result[title]) {
          console.log(`[知网下载链接提取器] 为页面标题找到下载链接: ${href}`);
          // 尝试找到页面上的作者、来源和日期信息
          const authors = document.querySelector('.author, .writers')?.innerText.trim() || "";
          const source = document.querySelector('.source, .from')?.innerText.trim() || "";
          const date = document.querySelector('.date, .pub-date')?.innerText.trim() || "";
          
          result[title] = {
            title: title,
            url: href,
            authors: authors,
            source: source,
            date: date
          };
        }
      });
    }
  }
})();
