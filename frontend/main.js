// Multilingual Video Subtitle Generator - Frontend Logic
document.addEventListener("DOMContentLoaded", () => {
    // API base URL - Empty string means relative to current domain
    const API_BASE = "";

    // App state machine variables
    let videoId = null;
    let originalFilename = "";
    let uploadedFile = null;
    let srtBlocks = [];
    let statusInterval = null;

    // DOM Elements
    const dropzone = document.getElementById("dropzone");
    const fileInput = document.getElementById("video-file-input");
    const fileInfo = document.getElementById("file-info");
    const selectedFileName = document.getElementById("selected-file-name");
    const removeFileBtn = document.getElementById("remove-file-btn");

    const uploadPanel = document.getElementById("upload-panel");
    const configPanel = document.getElementById("config-panel");
    const editorPanel = document.getElementById("editor-panel");
    const downloadPanel = document.getElementById("download-panel");

    const fontSelect = document.getElementById("font-name-select");
    const previewBox = document.getElementById("font-preview-box");
    const previewText = document.getElementById("font-preview-text");

    const prepareBtn = document.getElementById("prepare-subtitles-btn");
    const generateBtn = document.getElementById("generate-video-btn");
    const editStylesBackBtn = document.getElementById("edit-styles-back-btn");
    const editorReconfigureBtn = document.getElementById("editor-reconfigure-btn");
    const uploadAnotherBtn = document.getElementById("upload-another-btn");
    const startOverEditorBtn = document.getElementById("start-over-editor-btn");

    const timelineList = document.getElementById("timeline-list");
    const downloadVideoLink = document.getElementById("download-video-link");
    const downloadSrtBtn = document.getElementById("download-srt-btn");

    const loadingOverlay = document.getElementById("loading-overlay");
    const loadingTitle = document.getElementById("loading-title");
    const loadingSubtitle = document.getElementById("loading-subtitle");

    // --- Drag & Drop handlers ---
    ["dragenter", "dragover"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.add("dragover");
        }, false);
    });

    ["dragleave", "drop"].forEach(eventName => {
        dropzone.addEventListener(eventName, (e) => {
            e.preventDefault();
            dropzone.classList.remove("dragover");
        }, false);
    });

    dropzone.addEventListener("drop", (e) => {
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            handleFileSelection(files[0]);
        }
    });

    fileInput.addEventListener("change", (e) => {
        if (fileInput.files.length > 0) {
            handleFileSelection(fileInput.files[0]);
        }
    });

    removeFileBtn.addEventListener("click", () => {
        resetUploadState();
    });

    function handleFileSelection(file) {
        // Validate size (200MB limit)
        const maxSize = 200 * 1024 * 1024; // 200 MB
        if (file.size > maxSize) {
            alert("File is too large. Maximum allowed size is 200MB.");
            return;
        }

        // Validate format
        const ext = file.name.split('.').pop().toLowerCase();
        if (!["mp4", "avi", "mkv", "mov"].includes(ext)) {
            alert(`Unsupported file format '.${ext}'. Please upload MP4, AVI, MKV, or MOV.`);
            return;
        }

        uploadedFile = file;
        originalFilename = file.name;
        selectedFileName.textContent = originalFilename;
        
        dropzone.style.display = "none";
        fileInfo.style.display = "flex";

        // Trigger Upload automatically
        uploadVideoFile(file);
    }

    function resetUploadState() {
        uploadedFile = null;
        videoId = null;
        originalFilename = "";
        fileInput.value = "";
        dropzone.style.display = "block";
        fileInfo.style.display = "none";
        configPanel.style.display = "none";
        editorPanel.style.display = "none";
        downloadPanel.style.display = "none";
    }

    // --- Font Preview Synchronization ---
    function updateFontPreview() {
        const selectedFont = fontSelect.value;
        previewBox.style.fontFamily = `'${selectedFont}', sans-serif`;
        previewText.textContent = `${selectedFont} Style Preview`;
    }
    fontSelect.addEventListener("change", updateFontPreview);
    updateFontPreview(); // Run once initially

    // --- Loading Modal Trigger ---
    function showLoading(title, subtitle) {
        loadingTitle.textContent = title;
        loadingSubtitle.textContent = subtitle;
        loadingOverlay.style.display = "flex";
    }

    function hideLoading() {
        loadingOverlay.style.display = "none";
    }

    // --- API Calls ---

    // 1. Upload Video
    async function uploadVideoFile(file) {
        showLoading("Uploading Video", "Sending your video file to the server. Please wait...");
        
        const formData = new FormData();
        formData.append("file", file);

        try {
            const response = await fetch(`${API_BASE}/upload`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(errText || "Upload failed");
            }

            const data = await response.json();
            videoId = data.video_id;
            
            // Show config panel
            configPanel.style.display = "block";
            
            // Scroll to config panel
            configPanel.scrollIntoView({ behavior: "smooth" });
        } catch (error) {
            console.error(error);
            alert(`Upload failed: ${error.message}`);
            resetUploadState();
        } finally {
            hideLoading();
        }
    }

    // 2. Prepare & Edit Subtitles (Transcribe only)
    prepareBtn.addEventListener("click", async () => {
        if (!videoId) return;

        showLoading("Preparing Subtitles", "AI is transcribing and translating your video speech to compile subtitle text...");

        const formData = new FormData();
        formData.append("target_language", document.getElementById("target-lang-select").value);
        formData.append("model_size", document.getElementById("accuracy-select").value);
        formData.append("segmentation_mode", document.getElementById("timing-select").value);
        formData.append("bilingual", document.getElementById("bilingual-checkbox").checked);

        try {
            const response = await fetch(`${API_BASE}/transcribe/${videoId}`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(errText || "Transcription failed");
            }

            const data = await response.json();
            srtBlocks = data.blocks;

            // Load blocks into editor list
            renderEditorTimeline(srtBlocks);

            // Transition Panels
            configPanel.style.display = "none";
            uploadPanel.style.display = "none";
            editorPanel.style.display = "block";
            editorPanel.scrollIntoView({ behavior: "smooth" });

        } catch (error) {
            console.error(error);
            alert(`Transcription failed: ${error.message}`);
        } finally {
            hideLoading();
        }
    });

    // Render timeline segments in editor
    function renderEditorTimeline(blocks) {
        timelineList.innerHTML = "";

        if (blocks.length === 0) {
            timelineList.innerHTML = `<div style="text-align: center; padding: 20px; color: var(--text-secondary);">No speech detected in this video. You can type manual segments or skip.</div>`;
            return;
        }

        blocks.forEach((block) => {
            const card = document.createElement("div");
            card.className = "timeline-card";
            card.dataset.index = block.index;

            card.innerHTML = `
                <div class="segment-index">${block.index}</div>
                <div>
                    <input type="text" class="segment-time-input" value="${block.timestamp}" />
                </div>
                <div>
                    <textarea class="segment-text-input" rows="2">${block.text}</textarea>
                </div>
            `;
            timelineList.appendChild(card);
        });
    }

    // Get current edited segments from the DOM
    function getEditedSRTContent() {
        let content = "";
        const cards = timelineList.querySelectorAll(".timeline-card");
        
        cards.forEach((card) => {
            const idx = card.dataset.index;
            const time = card.querySelector(".segment-time-input").value;
            const text = card.querySelector(".segment-text-input").value.replace(/\n/g, " ");
            
            content += `${idx}\n${time}\n${text}\n\n`;
        });
        
        return content;
    }

    // 3. Generate Subtitled Video
    generateBtn.addEventListener("click", async () => {
        if (!videoId) return;

        showLoading("Submitting Video Task", "Burning subtitles onto video frame by frame...");

        // Compile edited SRT data to temporary file
        const srtContent = getEditedSRTContent();
        
        // Post the SRT file bytes and parameters to burn subtitles
        const srtBlob = new Blob([srtContent], { type: 'text/srt' });
        
        const formData = new FormData();
        formData.append("target_language", document.getElementById("target-lang-select").value);
        formData.append("alignment", document.getElementById("position-select").value);
        formData.append("font_size", document.getElementById("font-size-select").value);
        formData.append("font_color", document.getElementById("font-color-select").value);
        formData.append("email", document.getElementById("email-input").value);
        formData.append("model_size", document.getElementById("accuracy-select").value);
        formData.append("resolution_cap", document.getElementById("resolution-select").value);
        formData.append("segmentation_mode", document.getElementById("timing-select").value);
        formData.append("font_name", document.getElementById("font-name-select").value);
        formData.append("border_style", document.getElementById("bg-style-select").value);
        
        // Pass the edited SRT file
        formData.append("srt_file", srtBlob, "edited.srt");

        try {
            const response = await fetch(`${API_BASE}/process_custom/${videoId}`, {
                method: "POST",
                body: formData
            });

            if (!response.ok) {
                const errText = await response.text();
                throw new Error(errText || "Processing initiation failed");
            }

            const data = await response.json();
            
            // Start Polling
            pollTaskStatus(videoId);
        } catch (error) {
            console.error(error);
            alert(`Processing failed: ${error.message}`);
            hideLoading();
        }
    });

    // 4. Poll Status
    function pollTaskStatus(id) {
        showLoading("Generating Video", "Applying dynamic subtitles and presets. Please keep this browser window open...");

        statusInterval = setInterval(async () => {
            try {
                const response = await fetch(`${API_BASE}/status/${id}`);
                if (!response.ok) return;

                const data = await response.json();
                
                if (data.status === "completed") {
                    clearInterval(statusInterval);
                    hideLoading();
                    showDownloadDialog(id);
                } else if (data.status === "failed") {
                    clearInterval(statusInterval);
                    hideLoading();
                    alert(`Processing failed: ${data.error || "Unknown server error"}`);
                }
            } catch (error) {
                console.error("Error checking status:", error);
            }
        }, 1000); // Check every second
    }

    // 5. Show Final Panel
    function showDownloadDialog(id) {
        downloadVideoLink.href = `${API_BASE}/download/${id}`;
        
        // Transition Panel
        editorPanel.style.display = "none";
        downloadPanel.style.display = "block";
        downloadPanel.scrollIntoView({ behavior: "smooth" });
    }

    // Download SRT click handler
    downloadSrtBtn.addEventListener("click", () => {
        const srtContent = getEditedSRTContent();
        const blob = new Blob([srtContent], { type: "text/srt;charset=utf-8;" });
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.setAttribute("download", `${originalFilename.split('.')[0]}_subtitles.srt`);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    });

    // --- Back Navigation Handlers ---

    // Return to configurations panel
    editorReconfigureBtn.addEventListener("click", () => {
        editorPanel.style.display = "none";
        configPanel.style.display = "block";
        uploadPanel.style.display = "block";
        configPanel.scrollIntoView({ behavior: "smooth" });
    });

    editStylesBackBtn.addEventListener("click", () => {
        downloadPanel.style.display = "none";
        configPanel.style.display = "block";
        uploadPanel.style.display = "block";
        configPanel.scrollIntoView({ behavior: "smooth" });
    });

    // Start completely over
    startOverEditorBtn.addEventListener("click", () => {
        if (confirm("Are you sure you want to discard changes and start over?")) {
            resetUploadState();
        }
    });

    uploadAnotherBtn.addEventListener("click", () => {
        resetUploadState();
        window.scrollTo({ top: 0, behavior: "smooth" });
    });
});
