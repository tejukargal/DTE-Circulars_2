let isLoading = false;
let circularsData = [];
let currentCategory = 'Departmental';

// Dark mode functionality
function toggleDarkMode() {
    const html = document.documentElement;
    const toggleBtn = document.getElementById('darkModeToggle');
    
    if (html.getAttribute('data-theme') === 'dark') {
        // Switch to light mode
        html.removeAttribute('data-theme');
        toggleBtn.innerHTML = '🌙';
        localStorage.setItem('theme', 'light');
    } else {
        // Switch to dark mode
        html.setAttribute('data-theme', 'dark');
        toggleBtn.innerHTML = '☀️';
        localStorage.setItem('theme', 'dark');
    }
}

// Initialize theme on page load
function initializeTheme() {
    const savedTheme = localStorage.getItem('theme');
    const html = document.documentElement;
    const toggleBtn = document.getElementById('darkModeToggle');
    
    if (savedTheme === 'dark') {
        html.setAttribute('data-theme', 'dark');
        toggleBtn.innerHTML = '☀️';
    } else {
        html.removeAttribute('data-theme');
        toggleBtn.innerHTML = '🌙';
    }
}

function showLoading() {
    document.getElementById('loading').style.display = 'block';
    document.getElementById('error').style.display = 'none';
    document.getElementById('success').style.display = 'none';
    document.getElementById('stats').style.display = 'none';
    document.getElementById('circulars').innerHTML = '';
    document.getElementById('no-results').style.display = 'none';
    document.getElementById('exportBtn').style.display = 'none';
    document.querySelector('.refresh-btn').disabled = true;
    isLoading = true;
}

function hideLoading() {
    document.getElementById('loading').style.display = 'none';
    document.querySelector('.refresh-btn').disabled = false;
    isLoading = false;
}

function showError(message) {
    const errorDiv = document.getElementById('error');
    errorDiv.innerHTML = `
        <strong>⚠️ Data Loading Issue:</strong> ${message}
        <br><br>
        <strong>💡 What to try:</strong>
        <ul style="margin: 10px 0; padding-left: 20px;">
            <li>Wait a moment and click "Refresh Data" again</li>
            <li>The GitHub Actions may be updating the data</li>
            <li>Check back in a few minutes</li>
        </ul>
        <button onclick="loadCirculars()" style="background: #28a745; color: white; padding: 8px 16px; border: none; border-radius: 4px; cursor: pointer; margin-top: 10px;">
            🔄 Try Again
        </button>
    `;
    errorDiv.style.display = 'block';
}

function showSuccess(message) {
    const successDiv = document.getElementById('success');
    successDiv.innerHTML = message;
    successDiv.style.display = 'block';
    setTimeout(() => {
        successDiv.style.display = 'none';
    }, 5000);
}

function displayCirculars(circulars, timestamp) {
    const circularsDiv = document.getElementById('circulars');
    const statsDiv = document.getElementById('stats');
    const noResultsDiv = document.getElementById('no-results');
    const exportBtn = document.getElementById('exportBtn');

    if (!circulars || circulars.length === 0) {
        noResultsDiv.style.display = 'block';
        return;
    }

    // Show stats
    const lastUpdated = timestamp ? new Date(timestamp).toLocaleString('en-IN') : new Date().toLocaleString('en-IN');
    statsDiv.innerHTML = `
        <strong>📊 ${circulars.length} circulars loaded</strong> | 
        <strong>🕒 Last updated:</strong> ${lastUpdated} |
        <strong>🤖 Auto-refreshed:</strong> Every 30 minutes
    `;
    statsDiv.style.display = 'block';
    exportBtn.style.display = 'inline-block';

    // Display circulars
    const circularsHtml = circulars.map((circular, index) => {
        // Determine the header class based on category
        const headerClass = currentCategory.toLowerCase();
        
        // Create clean title
        let cleanTitle = circular.description || circular.title || 'No title available';
        cleanTitle = cleanTitle.replace(/^[^:]+:\s*/, ''); // Remove order number pattern from beginning
        
        return `
        <div class="circular-item">
            <div class="circular-header ${headerClass}">
                <div class="serial-number">${index + 1}</div>
                <div class="circular-title">
                    ${escapeHtml(cleanTitle)}
                </div>
            </div>
            <div class="circular-meta">
                <div class="meta-item">
                    <span>📅</span>
                    <span>Date: </span>
                    <span class="meta-date">${escapeHtml(circular.date || 'Not available')}</span>
                </div>
                ${circular.circular_no ? `
                <div class="meta-item">
                    <span>📋</span>
                    <span>Order: </span>
                    <span class="meta-order">${escapeHtml(circular.circular_no)}</span>
                </div>
                ` : ''}
                <div class="meta-item">
                    <span>🏛️</span>
                    <span>Section: </span>
                    <span class="meta-section">${getSectionName(currentCategory)}</span>
                </div>
            </div>
            <div class="circular-actions">
                <a href="${generatePDFLink(circular, currentCategory)}" target="_blank" class="circular-link">
                    ${(circular.download_link && circular.download_link !== '' && !circular.download_link.includes('atoall.com')) ? '📄 View PDF' : '🌐 View Source'}
                </a>
                <button onclick="shareCircular('${circular.download_link || ''}', '${escapeHtml(cleanTitle)}', '${escapeHtml(circular.date || '')}', '${escapeHtml(circular.circular_no || '')}', '${currentCategory}')" class="share-btn">
                    🔗 Share
                </button>
            </div>
        </div>
    `;
    }).join('');

    circularsDiv.innerHTML = circularsHtml;
    circularsData = circulars;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text || '';
    return div.innerHTML;
}

function getSectionName(category) {
    const sectionNames = {
        'DVP': 'DVP Circulars',
        'Departmental': 'Departmental Orders',
        'EST': 'EST Circulars',
        'ACM': 'ACM Polytechnic Circulars'
    };
    return sectionNames[category] || 'DTE Karnataka';
}

function generatePDFLink(circular, category) {
    // First try the actual download link if it exists and is valid
    if (circular.download_link && 
        circular.download_link !== null && 
        circular.download_link !== '' && 
        circular.download_link !== 'undefined' &&
        !circular.download_link.includes('atoall.com')) {
        return circular.download_link;
    }
    
    // For departmental circulars, use the specific departmental page
    if (category === 'Departmental') {
        return 'https://dtek.karnataka.gov.in/info-4/Departmental+Circulars/kn';
    }
    
    // For DVP category, use the DVP page
    if (category === 'DVP') {
        return 'https://dtek.karnataka.gov.in/page/Circulars/DVP/kn';
    }
    
    // For EST category, use the EST page
    if (category === 'EST') {
        return 'https://dtek.karnataka.gov.in/page/Circulars/EST/kn';
    }
    
    // For ACM category, use the ACM page
    if (category === 'ACM') {
        return 'https://dtek.karnataka.gov.in/page/Circulars/ACM-Polytechnic/kn';
    }
    
    // Fallback to the main circulars page
    return 'https://dtek.karnataka.gov.in/info-4/Departmental+Circulars/kn';
}

async function exportToPDF() {
    if (circularsData.length === 0) {
        showError('No data to export. Please refresh first.');
        return;
    }

    try {
        // Show loading state
        const exportBtn = document.getElementById('exportBtn');
        const originalText = exportBtn.innerHTML;
        exportBtn.innerHTML = '🔄 Generating PDF...';
        exportBtn.disabled = true;

        // Create a temporary container for PDF content with A4 portrait dimensions
        const pdfContainer = document.createElement('div');
        pdfContainer.style.cssText = `
            position: absolute;
            top: -9999px;
            left: -9999px;
            width: 794px;
            background: white;
            padding: 40px;
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #333;
            line-height: 1.5;
        `;

        // Create PDF content with table format
        const categoryName = getSectionName(currentCategory);
        let pdfContent = `
            <div style="text-align: center; margin-bottom: 25px; border-bottom: 2px solid #007bff; padding-bottom: 15px;">
                <h1 style="font-size: 22px; margin: 0; color: #007bff; font-weight: bold;">DTE Karnataka Circulars</h1>
                <p style="font-size: 16px; margin: 8px 0; color: #666; font-weight: 600;">Department: ${categoryName}</p>
                <p style="font-size: 13px; margin: 5px 0; color: #666;">Generated on: ${new Date().toLocaleDateString('en-IN')} | Total Records: ${circularsData.length}</p>
            </div>
        `;

        // Create table with optimized column widths for portrait mode
        pdfContent += `
            <table style="width: 100%; border-collapse: collapse; font-size: 10px; margin-top: 15px;">
                <thead>
                    <tr style="background-color: #007bff; color: white;">
                        <th style="border: 1px solid #333; padding: 8px 4px; text-align: center; font-weight: bold; width: 6%; font-size: 11px;">Sl</th>
                        <th style="border: 1px solid #333; padding: 8px 4px; text-align: center; font-weight: bold; width: 12%; font-size: 11px;">Date</th>
                        <th style="border: 1px solid #333; padding: 8px 4px; text-align: center; font-weight: bold; width: 22%; font-size: 11px;">Order No.</th>
                        <th style="border: 1px solid #333; padding: 8px 4px; text-align: center; font-weight: bold; width: 50%; font-size: 11px;">Subject</th>
                        <th style="border: 1px solid #333; padding: 8px 4px; text-align: center; font-weight: bold; width: 10%; font-size: 11px;">Section</th>
                    </tr>
                </thead>
                <tbody>
        `;

        // Add table rows for each circular
        circularsData.forEach((circular, index) => {
            let cleanTitle = (circular.description || circular.title || 'No title available').replace(/^[^:]+:\s*/, '');
            const backgroundColor = index % 2 === 0 ? '#f8f9fa' : '#ffffff';
            
            pdfContent += `
                <tr style="background-color: ${backgroundColor}; page-break-inside: avoid;">
                    <td style="border: 1px solid #333; padding: 6px 3px; text-align: center; vertical-align: top; font-weight: 600; color: #007bff; font-size: 10px;">
                        ${index + 1}
                    </td>
                    <td style="border: 1px solid #333; padding: 6px 3px; text-align: center; vertical-align: top; font-size: 9px; line-height: 1.2;">
                        ${circular.date || 'N/A'}
                    </td>
                    <td style="border: 1px solid #333; padding: 6px 3px; vertical-align: top; font-size: 9px; word-wrap: break-word; line-height: 1.3;">
                        ${circular.circular_no || 'N/A'}
                    </td>
                    <td style="border: 1px solid #333; padding: 6px 3px; vertical-align: top; font-size: 9px; word-wrap: break-word; line-height: 1.4; text-align: left;">
                        ${cleanTitle}
                    </td>
                    <td style="border: 1px solid #333; padding: 6px 3px; text-align: center; vertical-align: top; font-size: 8px; font-weight: 600; color: #28a745; line-height: 1.2;">
                        ${getSectionName(currentCategory).replace('Circulars', '').replace('Orders', '').trim()}
                    </td>
                </tr>
            `;
        });

        // Close table and add footer
        pdfContent += `
                </tbody>
            </table>
            
            <div style="text-align: center; margin-top: 30px; padding-top: 20px; border-top: 2px solid #007bff; font-size: 12px; color: #666;">
                <p style="margin: 5px 0;"><strong>Generated from DTE Karnataka Circulars App</strong></p>
                <p style="margin: 5px 0;">Official Website: https://dtek.karnataka.gov.in/</p>
                <p style="margin: 5px 0; font-size: 11px; opacity: 0.8;">This document contains ${circularsData.length} circulars from ${categoryName}</p>
            </div>
        `;

        pdfContainer.innerHTML = pdfContent;
        document.body.appendChild(pdfContainer);

        // Wait a moment for fonts to load and content to render
        await new Promise(resolve => setTimeout(resolve, 600));

        // Convert to canvas with optimized settings for A4 portrait
        const canvas = await html2canvas(pdfContainer, {
            scale: 3,
            useCORS: true,
            allowTaint: true,
            backgroundColor: '#ffffff',
            width: 794,
            windowWidth: 794,
            scrollX: 0,
            scrollY: 0
        });

        // Create PDF with portrait orientation for A4 size
        const { jsPDF } = window.jspdf;
        const pdf = new jsPDF('portrait', 'mm', 'a4');
        
        const pdfWidth = 210;
        const pdfHeight = 297;
        const canvasWidth = canvas.width;
        const canvasHeight = canvas.height;
        
        // Calculate proper scaling for full A4 width utilization
        const margin = 5;
        const availableWidth = pdfWidth - (margin * 2);
        const availableHeight = pdfHeight - (margin * 2);
        
        // Scale to fit width while maintaining aspect ratio
        const scale = availableWidth / (canvasWidth / 3);
        const scaledWidth = availableWidth;
        const scaledHeight = (canvasHeight / 3) * scale;
        
        // Calculate how many pages we need
        let currentHeight = 0;
        let pageNumber = 1;

        while (currentHeight < canvasHeight) {
            const remainingHeight = canvasHeight - currentHeight;
            const maxPageHeight = (availableHeight * canvasHeight) / scaledHeight;
            const pageCanvasHeight = Math.min(remainingHeight, maxPageHeight);
            
            // Create a temporary canvas for this page
            const pageCanvas = document.createElement('canvas');
            const pageCtx = pageCanvas.getContext('2d');
            pageCanvas.width = canvasWidth;
            pageCanvas.height = pageCanvasHeight;
            
            // Fill with white background
            pageCtx.fillStyle = '#ffffff';
            pageCtx.fillRect(0, 0, canvasWidth, pageCanvasHeight);
            
            // Draw the portion of the main canvas
            pageCtx.drawImage(
                canvas,
                0, currentHeight, canvasWidth, pageCanvasHeight,
                0, 0, canvasWidth, pageCanvasHeight
            );
            
            // Add to PDF
            const imgData = pageCanvas.toDataURL('image/jpeg', 0.95);
            
            if (pageNumber > 1) {
                pdf.addPage();
            }
            
            const pageHeight = (pageCanvasHeight / 3) * scale;
            pdf.addImage(imgData, 'JPEG', margin, margin, scaledWidth, pageHeight);
            
            currentHeight += pageCanvasHeight;
            pageNumber++;
        }

        // Clean up
        document.body.removeChild(pdfContainer);

        // Save the PDF
        const fileName = `DTE_${currentCategory}_Circulars_${new Date().toISOString().split('T')[0]}.pdf`;
        pdf.save(fileName);
        
        showSuccess('📄 PDF exported successfully!');
        
    } catch (error) {
        console.error('PDF Export Error:', error);
        showError('Failed to export PDF. Please try again.');
    } finally {
        // Restore button state
        const exportBtn = document.getElementById('exportBtn');
        exportBtn.innerHTML = '📄 Export PDF';
        exportBtn.disabled = false;
    }
}

function changeCategory(category) {
    // Remove active class from all tabs
    document.querySelectorAll('.tab').forEach(tab => {
        tab.classList.remove('active');
    });
    
    // Add active class to clicked tab
    const clickedTab = document.querySelector(`[data-category="${category}"]`);
    if (clickedTab) {
        clickedTab.classList.add('active');
    }
    
    currentCategory = category;
    loadCirculars();
}

async function loadCirculars() {
    if (isLoading) return;

    showLoading();

    try {
        // Load circulars data from our JSON file
        const response = await fetch('circulars.json');
        
        if (!response.ok) {
            throw new Error(`Failed to load circulars data (${response.status})`);
        }
        
        const data = await response.json();
        
        // Filter circulars based on current category
        let filteredCirculars = data.circulars || [];
        
        if (currentCategory === 'Departmental') {
            filteredCirculars = filteredCirculars.filter(circular => 
                // Include Departmental circulars and exclude DVP circulars
                (circular.source_url && circular.source_url.includes('Departmental+Circulars')) ||
                (!circular.circular_no?.includes('ಡಿವಿಪಿ') && !circular.circular_no?.includes('DVP'))
            );
            // Remove DVP circulars from Departmental category
            filteredCirculars = filteredCirculars.filter(circular => 
                !circular.circular_no?.includes('ಡಿವಿಪಿ') && !circular.circular_no?.includes('DVP')
            );
        } else if (currentCategory === 'DVP') {
            filteredCirculars = filteredCirculars.filter(circular => 
                // Include DVP circulars based on source URL or circular number patterns
                (circular.source_url && circular.source_url.includes('Circulars/DVP')) ||
                circular.circular_no?.includes('ಡಿವಿಪಿ') || 
                circular.circular_no?.includes('DVP') ||
                circular.download_link?.includes('/DVP/')
            );
        } else if (currentCategory === 'EST') {
            filteredCirculars = filteredCirculars.filter(circular => 
                // Include EST circulars based on source URL
                circular.source_url && circular.source_url.includes('Circulars/EST')
            );
        } else if (currentCategory === 'ACM') {
            filteredCirculars = filteredCirculars.filter(circular => 
                // Include ACM circulars based on source URL
                circular.source_url && circular.source_url.includes('Circulars/ACM')
            );
        }

        displayCirculars(filteredCirculars, data.last_updated);
        
        if (filteredCirculars.length > 0) {
            showSuccess(`✅ Successfully loaded ${filteredCirculars.length} ${currentCategory.toLowerCase()} circulars!`);
        }
    } catch (error) {
        showError(`Failed to load data: ${error.message}. The GitHub Actions may be updating the data.`);
        console.error('Load error:', error);
    } finally {
        hideLoading();
    }
}

// Share Circular Functionality
function shareCircular(pdfUrl, title, date, orderNumber, category) {
    const categoryName = getSectionName(category);
    
    // Build comprehensive share message with clean formatting
    let shareText = `📄 DTE Karnataka Circular\n`;
    shareText += `🏛️ Department: ${categoryName}\n\n`;
    shareText += `**Subject:** ${title}\n\n`;
    shareText += `**Date:** ${date}\n\n`;
    if (orderNumber) {
        shareText += `**Order No:** ${orderNumber}\n\n`;
    }
    
    // Handle document link
    if (pdfUrl && pdfUrl !== 'N/A' && pdfUrl !== 'null' && pdfUrl !== '') {
        shareText += `📄 Document available online`;
    } else {
        shareText += `📄 Document: Check official DTE website`;
    }
    
    // Try to use Web Share API if available
    if (navigator.share) {
        navigator.share({
            title: `DTE Karnataka Circular - ${title}`,
            text: shareText,
            url: (pdfUrl && pdfUrl !== 'N/A' && pdfUrl !== 'null' && pdfUrl !== '') ? pdfUrl : undefined
        }).then(() => {
            showSuccess('📤 Circular shared successfully!');
        }).catch((error) => {
            console.log('Error sharing:', error);
            fallbackShareCircular(shareText, pdfUrl);
        });
    } else {
        fallbackShareCircular(shareText, pdfUrl);
    }
}

function fallbackShareCircular(shareText, pdfUrl) {
    // Create a modal-like sharing interface
    const shareModal = document.createElement('div');
    shareModal.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: rgba(0,0,0,0.8);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 1000;
        font-family: inherit;
    `;
    
    const shareContent = document.createElement('div');
    shareContent.style.cssText = `
        background: var(--bg-secondary);
        color: var(--text-primary);
        padding: 30px;
        border-radius: 12px;
        max-width: 500px;
        width: 90%;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    `;
    
    shareContent.innerHTML = `
        <h3 style="margin: 0 0 20px 0; text-align: center; color: var(--text-primary);">Share Circular</h3>
        <div style="background: var(--bg-primary); padding: 15px; border-radius: 8px; margin-bottom: 20px; font-size: 14px; line-height: 1.6; white-space: pre-line;">${shareText}</div>
        <div style="display: flex; gap: 10px; flex-wrap: wrap;">
            <button id="copyTextBtn" style="flex: 1; padding: 12px; background: #28a745; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">📋 Copy Text</button>
            ${(pdfUrl && pdfUrl !== 'N/A' && pdfUrl !== 'null' && pdfUrl !== '') ? `<button id="viewPdfBtn" style="flex: 1; padding: 12px; background: #007bff; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">📄 View PDF</button>` : ''}
            <button id="closeModalBtn" style="flex: 1; padding: 12px; background: #6c757d; color: white; border: none; border-radius: 6px; cursor: pointer; font-size: 14px;">✖️ Close</button>
        </div>
    `;
    
    shareModal.appendChild(shareContent);
    document.body.appendChild(shareModal);
    
    // Add event listeners
    document.getElementById('copyTextBtn').onclick = () => {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(shareText).then(() => {
                showSuccess('📋 Circular details copied to clipboard!');
                document.body.removeChild(shareModal);
            });
        } else {
            manualShareCircular(shareText);
            document.body.removeChild(shareModal);
        }
    };
    
    if (pdfUrl && pdfUrl !== 'N/A' && pdfUrl !== 'null' && pdfUrl !== '') {
        document.getElementById('viewPdfBtn').onclick = () => {
            window.open(pdfUrl, '_blank');
            document.body.removeChild(shareModal);
        };
    }
    
    document.getElementById('closeModalBtn').onclick = () => {
        document.body.removeChild(shareModal);
    };
    
    // Close on background click
    shareModal.onclick = (e) => {
        if (e.target === shareModal) {
            document.body.removeChild(shareModal);
        }
    };
}

function manualShareCircular(shareText) {
    // Manual copy fallback
    const textArea = document.createElement('textarea');
    textArea.value = shareText;
    document.body.appendChild(textArea);
    textArea.focus();
    textArea.select();
    
    try {
        document.execCommand('copy');
        showSuccess('📋 Circular details copied to clipboard!');
    } catch (err) {
        prompt('Copy this circular information to share:', shareText);
    }
    
    document.body.removeChild(textArea);
}

// Load circulars when page loads
window.addEventListener('load', () => {
    // Initialize theme first
    initializeTheme();
    
    // Small delay to let the page render
    setTimeout(loadCirculars, 500);
    
    // Hide the auto-update info message after 5 seconds
    setTimeout(() => {
        const autoUpdateInfo = document.getElementById('autoUpdateInfo');
        if (autoUpdateInfo) {
            autoUpdateInfo.style.transition = 'opacity 0.5s ease-out';
            autoUpdateInfo.style.opacity = '0';
            setTimeout(() => {
                autoUpdateInfo.style.display = 'none';
            }, 500);
        }
    }, 5000);
});

// Handle keyboard shortcuts
document.addEventListener('keydown', (e) => {
    if (e.key === 'F5' || (e.ctrlKey && e.key === 'r')) {
        e.preventDefault();
        loadCirculars();
    }
});