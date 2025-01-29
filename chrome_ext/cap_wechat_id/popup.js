/*
* CREATED DATE: Wed Jan 29 15:48:37 2025
* CREATED BY: qiangxu, toxuqiang@gmail.com
*/
document.getElementById('extract').addEventListener('click', async () => {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  
  const injectionResults = await chrome.scripting.executeScript({
    target: { tabId: tab.id },
    func: () => {
      const accountRows = document.querySelectorAll('.AccountRow_account__D0wq_');
      const results = [];
      
      accountRows.forEach(row => {
        const displayNameEl = row.querySelector('span[title].hover\\:text-primary');
        const accountIdEl = row.querySelector('span[title]:not(.hover\\:text-primary)');
        
        if (displayNameEl && accountIdEl) {
          results.push({
            displayName: displayNameEl.textContent.trim(),
            accountId: accountIdEl.getAttribute('title')
          });
        }
      });
      
      return results;
    }
  });

  const accountInfo = injectionResults[0].result;
  
  // Display results in popup
  const resultsDiv = document.getElementById('results');
  if (accountInfo.length > 0) {
    resultsDiv.innerHTML = accountInfo.map(info => `
      <div class="result">
        <div>NAME: ${info.displayName}</div>
        <div>ID  : ${info.accountId}</div>
      </div>
    `).join('');

    // Create and download JSON file
    const jsonString = JSON.stringify(accountInfo, null, 2);
    const blob = new Blob([jsonString], { type: 'application/json' });
    
    // Generate filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
    const filename = `cap_wechat_id_${timestamp}.json`;
    
    // Create download link and trigger download
    const downloadLink = document.createElement('a');
    downloadLink.href = URL.createObjectURL(blob);
    downloadLink.download = filename;
    
    // Append link, click it, and remove it
    document.body.appendChild(downloadLink);
    downloadLink.click();
    document.body.removeChild(downloadLink);
    
    // Clean up the URL object
    setTimeout(() => {
      URL.revokeObjectURL(downloadLink.href);
    }, 100);
  } else {
    resultsDiv.innerHTML = 'NO ACCOUNT INFORMATION FOUND';
  }
});
