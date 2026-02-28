document.addEventListener('DOMContentLoaded', async () => {
    console.log('Initializing Original Resume Parser logic...');

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
    const dropZone = document.getElementById('drop-zone');
    const analyzeBtn = document.getElementById('analyze-btn');
    const fileNameDisplay = document.getElementById('file-name');
    const loadingDiv = document.getElementById('loading');

    const uploadView = document.getElementById('upload-view');
    const dashboardView = document.getElementById('dashboard-view');
    const backBtn = document.getElementById('back-btn');

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
            analyzeBtn.disabled = false;
        } else {
            fileNameDisplay.classList.add('hidden');
            analyzeBtn.disabled = true;
        }
    }

    // 3. Form Submission
    uploadForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const formData = new FormData();
        formData.append('resume', fileInput.files[0]);

        loadingDiv.classList.remove('hidden');
        analyzeBtn.disabled = true;
        uploadForm.style.opacity = '0.5';

        try {
            const response = await fetch('/analyze', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();

            if (!response.ok || data.error) {
                alert(data.error || 'Failed to analyze resume.');
                return;
            }

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

    // 4. Rendering Original Dashboard
    function renderDashboard(data) {
        console.log("Original parsed payload:", data);

        // -- ATS Score (Basic) --
        const totalScore = data.ats_score || 0;
        const atsCircle = document.getElementById('ats-circle');
        const atsText = document.getElementById('ats-text');

        if (atsCircle) atsCircle.setAttribute('stroke-dasharray', `${totalScore}, 100`);
        if (atsText) atsText.textContent = `${totalScore}%`;

        // -- Skills (Basic) --
        const techSkillsList = document.getElementById('tech-skills-list');
        const softSkillsList = document.getElementById('soft-skills-list');
        techSkillsList.innerHTML = '';
        softSkillsList.innerHTML = '';

        if (data.technical_skills) {
            Object.values(data.technical_skills).flat().forEach(skill => {
                const span = document.createElement('span');
                span.className = 'skill-tag';
                span.textContent = skill;
                techSkillsList.appendChild(span);
            });
        }

        if (data.soft_skills) {
            data.soft_skills.forEach(skill => {
                const span = document.createElement('span');
                span.className = 'skill-tag soft-skill';
                span.textContent = skill;
                softSkillsList.appendChild(span);
            });
        }

        // -- Roles --
        const rolesList = document.getElementById('roles-list');
        rolesList.innerHTML = '';
        if (data.job_roles) {
            data.job_roles.forEach(role => {
                const div = document.createElement('div');
                div.className = 'role-card';
                div.innerHTML = `<h4>${role.title}</h4><p>${role.description}</p>`;
                rolesList.appendChild(div);
            });
        }

        // -- Basic AI Suggestions --
        const tipsList = document.getElementById('ats-tips-list');
        tipsList.innerHTML = '';
        (data.ats_tips || []).forEach(tip => {
            const li = document.createElement('li');
            li.style.marginBottom = '10px';
            li.style.color = "var(--text-secondary)";
            li.style.position = "relative";
            li.style.paddingLeft = "20px";
            li.innerHTML = `<span style="position:absolute; left:0; color:#8b5cf6;">•</span> ${tip}`;
            tipsList.appendChild(li);
        });

        // -- Critical Gaps --
        const gapsList = document.getElementById('missing-skills-list');
        gapsList.innerHTML = '';
        const missing = data.missing_skills || [];
        if (missing.length === 0) {
            gapsList.innerHTML = '<p style="color:#34d399">Great job! No critical skill gaps identified.</p>';
        } else {
            missing.forEach(item => {
                const div = document.createElement('div');
                div.className = 'gap-item';
                div.innerHTML = `<span class="gap-skill-name">${item.skill}</span><span class="gap-rec">Tip: ${item.recommendation}</span>`;
                gapsList.appendChild(div);
            });
        }
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

});
