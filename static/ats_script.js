document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing ATS Engine frontend logic...');

    // 1. Setup Dropdown Menus & Auth
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', async (e) => {
            e.preventDefault();
            try {
                const res = await fetch('/logout', { method: 'POST' });
                if (res.ok) window.location.href = '/login';
            } catch (err) { }
        });
    }

    // Close dropdown if clicked outside
    window.addEventListener('click', function (e) {
        const menu = document.querySelector('.user-menu');
        if (menu && !menu.contains(e.target)) {
            const dropdown = document.getElementById('dropdown-menu');
            if (dropdown && !dropdown.classList.contains('hidden')) {
                dropdown.classList.add('hidden');
            }
        }
    });

    // 2. Setup Upload and Form
    const uploadForm = document.getElementById('upload-form');
    const fileInput = document.getElementById('file-input');
    const jdInput = document.getElementById('jd-input');
    const dropZone = document.getElementById('drop-zone');
    const analyzeBtn = document.getElementById('analyze-btn');
    const fileNameDisplay = document.getElementById('file-name');
    const loadingDiv = document.getElementById('loading');
    const jdError = document.getElementById('jd-error');

    const uploadView = document.getElementById('upload-view');
    const dashboardView = document.getElementById('dashboard-view');
    const backBtn = document.getElementById('back-btn');

    let currentReportData = null; // Store for PDF generation later if needed

    if (!uploadForm) return; // Not on the main page

    // Drag & Drop
    dropZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });

    dropZone.addEventListener('dragleave', () => {
        dropZone.classList.remove('dragover');
    });

    dropZone.addEventListener('drop', (e) => {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        if (e.dataTransfer.files.length) {
            fileInput.files = e.dataTransfer.files;
            handleFileSelect();
        }
    });

    fileInput.addEventListener('change', handleFileSelect);

    function handleFileSelect() {
        if (fileInput.files.length) {
            const file = fileInput.files[0];
            fileNameDisplay.textContent = `Attached: ${file.name}`;
            fileNameDisplay.classList.remove('hidden');
            checkFormValidity();
        } else {
            fileNameDisplay.classList.add('hidden');
            checkFormValidity();
        }
    }

    jdInput.addEventListener('input', checkFormValidity);

    function checkFormValidity() {
        const fileValid = fileInput.files.length > 0;
        analyzeBtn.disabled = !fileValid;
    }

    // 3. Form Submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData();
        formData.append('resume', fileInput.files[0]);
        formData.append('job_description', jdInput.value.trim());

        loadingDiv.classList.remove('hidden');
        analyzeBtn.disabled = true;
        uploadForm.style.opacity = '0.5';

        try {
            const response = await fetch('/analyze_ats', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                alert(data.error || 'Failed to analyze resume.');
                return;
            }

            currentReportData = data;
            renderDashboard(data);
            switchView('dashboard');
        } catch (err) {
            console.error(err);
            alert('An error occurred during analysis.');
        } finally {
            loadingDiv.classList.add('hidden');
            analyzeBtn.disabled = false;
            uploadForm.style.opacity = '1';
        }
    });

    // 4. Rendering Dashboard
    function renderDashboard(data) {
        console.log("Rendering payload:", data);

        // -- Info --
        const infoMsg = document.getElementById('candidate-info');
        if (infoMsg && data.info) {
            const n = data.info.name || "Candidate";
            const e = data.info.email || "No email detected";
            infoMsg.innerHTML = `<strong>${n}</strong> • ${e}`;
        }

        // -- ATS Score --
        const totalScore = data.score.total_score || 0;
        const atsCircle = document.getElementById('ats-circle');
        const atsText = document.getElementById('ats-text');

        if (atsCircle) atsCircle.setAttribute('stroke-dasharray', `${totalScore}, 100`);
        if (atsText) atsText.textContent = `${totalScore}%`;

        // Progress Bars Breakdown
        const bd = data.score.breakdown || {};
        const kwPct = Math.min(100, (bd.keyword_score / 40) * 100);
        const fmtPct = Math.min(100, (bd.format_score / 15) * 100);

        document.getElementById('kw-bar').style.width = `${kwPct}%`;
        document.getElementById('fmt-bar').style.width = `${fmtPct}%`;

        // -- Sections Detected --
        const secList = document.getElementById('sections-list');
        secList.innerHTML = '';
        for (const [secName, status] of Object.entries(data.sections || {})) {
            const span = document.createElement('span');
            span.className = `section-tag ${status === 'Found' ? 'section-found' : 'section-missing'}`;
            span.innerHTML = status === 'Found' ? `✓ ${secName}` : `✕ ${secName}`;
            secList.appendChild(span);
        }

        // -- Keywords --
        const kwRender = (id, arr) => {
            const el = document.getElementById(id);
            el.innerHTML = '';
            if (!arr || arr.length === 0) {
                el.innerHTML = '<span style="color:var(--text-secondary); font-size:0.85rem;">None</span>';
            } else {
                arr.forEach(k => {
                    const span = document.createElement('span');
                    span.className = 'skill-tag';
                    span.textContent = k;
                    el.appendChild(span);
                });
            }
        };
        kwRender('matched-kws', data.keywords.matched);
        kwRender('missing-kws', data.keywords.missing);
        kwRender('extra-kws', data.keywords.extra);

        // -- AI Suggestions --
        const ai = data.ai_analysis || {};
        const tipsList = document.getElementById('ats-tips-list');
        tipsList.innerHTML = '';
        (ai.ats_tips || []).forEach(tip => {
            const li = document.createElement('li');
            li.style.marginBottom = '10px';
            li.style.color = "var(--text-secondary)";
            li.style.position = "relative";
            li.style.paddingLeft = "20px";
            li.innerHTML = `<span style="position:absolute; left:0; color:#8b5cf6;">•</span> ${tip}`;
            tipsList.appendChild(li);
        });


    }

    // 5. View Switching
    function switchView(viewName) {
        if (viewName === 'dashboard') {
            uploadView.classList.remove('active');
            uploadView.classList.add('hidden');
            dashboardView.classList.remove('hidden');
            setTimeout(() => dashboardView.classList.add('active'), 50);
        } else {
            dashboardView.classList.remove('active');
            dashboardView.classList.add('hidden');
            uploadView.classList.remove('hidden');
            setTimeout(() => uploadView.classList.add('active'), 50);
        }
    }

    backBtn.addEventListener('click', () => {
        switchView('upload');
        uploadForm.reset();
        fileNameDisplay.classList.add('hidden');
        analyzeBtn.disabled = true;
    });

    // 6. Sentence Improver AI
    const improveBtn = document.getElementById('improve-btn');
    const sentenceInput = document.getElementById('sentence-input');
    const improvedResult = document.getElementById('improved-result');
    const improvedText = document.getElementById('improved-text');

    if (improveBtn) {
        improveBtn.addEventListener('click', async () => {
            const sentence = sentenceInput.value.trim();
            if (!sentence) return;

            improveBtn.disabled = true;
            improveBtn.textContent = 'Rewriting...';
            improvedResult.classList.add('hidden');

            try {
                const res = await fetch('/improve_sentence', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sentence: sentence })
                });
                const data = await res.json();

                if (data.improved) {
                    improvedText.textContent = data.improved;
                    improvedResult.classList.remove('hidden');
                } else {
                    alert("Failed to improve sentence.");
                }
            } catch (e) {
                console.error(e);
                alert("Network error.");
            } finally {
                improveBtn.disabled = false;
                improveBtn.textContent = 'Rewrite with AI';
            }
        });
    }

    // 7. Download PDF Report
    const exportBtn = document.getElementById('export-report-btn');
    if (exportBtn) {
        exportBtn.addEventListener('click', async () => {
            if (!currentReportData) return;

            exportBtn.disabled = true;
            const originalText = exportBtn.innerHTML;
            exportBtn.innerHTML = 'Downloading...';

            try {
                const res = await fetch('/download_report', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(currentReportData)
                });

                if (!res.ok) throw new Error("Failed");

                // Tricky way to download a blob via Fetch
                const blob = await res.blob();
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = 'Smart_ATS_Report.pdf';
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
            } catch (err) {
                console.error(err);
                alert('Failed to generate report.');
            } finally {
                exportBtn.disabled = false;
                exportBtn.innerHTML = originalText;
            }
        });
    }
});
