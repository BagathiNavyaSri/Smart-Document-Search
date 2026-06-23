let currentChatId = null;

let allChats = JSON.parse(

    localStorage.getItem(

        `allChats_${localStorage.getItem("email")}`
    )

) || [];

const uploadedFilesContainer =
    document.getElementById(
        "uploadedFilesContainer"
    );

const fileCount =
    document.getElementById(
        "fileCount"
    );

const dropZone = document.getElementById("dropZone");

const fileInput = document.getElementById("fileInput");

const sendBtn = document.getElementById("sendBtn");

const questionInput = document.getElementById("questionInput");

const chatSection =
    document.getElementById("chatSection");

// =========================================
// LOAD USER PROFILE
// =========================================

const profileName =
    document.getElementById("profileName");

const profileEmail =
    document.getElementById("profileEmail");

const storedUsername =
    localStorage.getItem("username");

const storedEmail =
    localStorage.getItem("email");

function saveCurrentChat(
    question,
    answer,
    sources = []
) {

    if (!currentChatId) {

        currentChatId = Date.now();
    }

    let existingChat = allChats.find(
        chat => chat.id === currentChatId
    );

    if (!existingChat) {

        existingChat = {

            id: currentChatId,

            title: question,

            messages: []
        };

        allChats.unshift(existingChat);
    }

    // Extract primary filename from sources
    let primaryFilename = "No source";
    if (sources && sources.length > 0) {
        primaryFilename = sources[0].filename || "Unknown File";
    }

    existingChat.messages.push({

        question,
        answer,
        filename: primaryFilename,
        sources: sources,
        timestamp: new Date().toISOString()
    });

    localStorage.setItem(
        `allChats_${localStorage.getItem("email")}`,
        JSON.stringify(allChats)
    );

    renderChatHistory();
}

if (profileName && storedUsername) {

    profileName.innerText =
        storedUsername;
}

if (profileEmail && storedEmail) {

    profileEmail.innerText =
        storedEmail;
}
// =========================================
// DRAG & DROP
// =========================================

dropZone.addEventListener("click", () => {
    fileInput.click();
});

dropZone.addEventListener("dragover", (e) => {

    e.preventDefault();

    dropZone.classList.add("drag-active");
});

dropZone.addEventListener("dragleave", () => {

    dropZone.classList.remove("drag-active");
});

dropZone.addEventListener("drop", async (e) => {

    e.preventDefault();

    dropZone.classList.remove("drag-active");

    const files = Array.from(e.dataTransfer.files);

    uploadFiles(files);
});

fileInput.addEventListener("change", async (e) => {

    e.preventDefault();
    const files = Array.from(fileInput.files);
    console.log("FILES:", files.length);
    await uploadFiles(files);
    fileInput.value = "";
});


// =========================================
// UPLOAD FILES
// =========================================

async function uploadFiles(files) {

    const formData = new FormData();

    files.forEach((file) => {

        formData.append("file", file);

        addMessage(
            "AI",
            `Uploading ${file.name}...`
        );
    });

    formData.append(
        "email",
        localStorage.getItem("email")
    );

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/upload",
            {
                method: "POST",
                body: formData
            }
        );

        const data = await response.json();

        if (!response.ok) {

            addMessage(
                "AI",
                `❌ Upload failed: ${data.detail || "Please try again."}`
            );

            return;
        }

        if (Array.isArray(data.uploads)) {

            data.uploads.forEach((result) => {

                if (result.success) {

                    addMessage(
                        "AI",
                        `✅ ${result.filename} uploaded successfully.\n\nChunks Indexed: ${result.total_chunks}`
                    );

                } else {

                    addMessage(
                        "AI",
                        `⚠️ ${result.filename} upload failed: ${result.error}`
                    );
                }
            });

        } else if (data.total_chunks !== undefined) {

            addMessage(
                "AI",
                `✅ ${files[0].name} uploaded successfully.\n\nChunks Indexed: ${data.total_chunks}`
            );
        }

    } catch (error) {

        addMessage(
            "AI",
            `❌ Failed to upload files: ${error.message}`
        );
    }

    loadUploadedFiles();
}

// =========================================
// ADD MESSAGE (WITH FILENAME SUPPORT)
// =========================================

function addMessage(sender, text, filename = null) {

    const wrapper = document.createElement("div");

    wrapper.className = `
        flex gap-4 fade-in
    `;

    // Build filename header if provided
    let filenameHTML = "";
    if (filename && sender === "AI") {
        filenameHTML = `<p class="text-xs text-cyan-400 mb-2 font-semibold">📄 Source: ${filename}</p>`;
    }

    wrapper.innerHTML = `

    <div
        class="w-12 h-12 rounded-full bg-cyan-500 flex items-center justify-center font-bold text-black flex-shrink-0">

        ${sender === "AI" ? "AI" : "U"}

    </div>

    <div
        class="inline-block bg-[#1e293b] border border-gray-700 rounded-2xl px-4 py-3 text-white max-w-[75%]">

        ${filenameHTML}
        
        <p class="leading-6 whitespace-pre-line text-sm font-medium text-white">

            ${text}

        </p>

    </div>
`;

    chatSection.appendChild(wrapper);

    chatSection.scrollTop =
        chatSection.scrollHeight;
}

// =========================================
// ASK QUESTION
// =========================================

function normalizeSourceForUI(source) {
    const filename = source?.filename || "Unknown File";
    let pageNumber = source?.page_number;

    if (pageNumber === undefined || pageNumber === null || pageNumber === "") {
        pageNumber = "N/A";
    } else {
        pageNumber = String(pageNumber);
    }

    const confidence = Number.isFinite(Number(source?.confidence))
        ? Math.round(Number(source.confidence))
        : 0;

    const chunkText = typeof source?.chunk === "string" && source.chunk.trim()
        ? source.chunk.trim()
        : "No relevant context available.";

    const filepath = typeof source?.filepath === "string"
        ? source.filepath.replace(/\\/g, "/")
        : "";

    let sourceUrl = "";
    if (filepath.startsWith("uploads/")) {
        sourceUrl = `http://127.0.0.1:8000/${filepath}`;
    } else if (filepath.includes("/uploads/")) {
        const relativePath = filepath.split("/uploads/")[1];
        sourceUrl = `http://127.0.0.1:8000/uploads/${relativePath}`;
    } else if (filepath) {
        sourceUrl = `http://127.0.0.1:8000/uploads/${filepath.split("/").pop()}`;
    }

    return {
        filename,
        pageNumber,
        confidence,
        chunkText,
        sourceUrl,
        filepath,
        chunkId: source?.chunk_id,
        documentId: source?.document_id
    };
}

function buildSourceCards(sources) {
    const uniqueSources = [];
    const seenKeys = new Set();

    (sources || []).forEach((source) => {
        const normalized = normalizeSourceForUI(source);
        const preview = normalized.chunkText.substring(0, 120).trim();
        const key = `${normalized.filename}-${normalized.pageNumber}-${preview}`;

        if (!seenKeys.has(key)) {
            seenKeys.add(key);
            uniqueSources.push(normalized);
        }
    });

    return uniqueSources.map((source) => `
        <div class="mt-4 border border-gray-600 rounded-lg p-4 bg-[#0f172a] hover:border-cyan-400 transition-colors duration-200">
            <div class="flex items-start justify-between gap-3 mb-3">
                <div class="flex-1 min-w-0">
                    <p class="text-cyan-400 font-semibold text-sm truncate">
                        📄 ${source.filename}
                    </p>
                    <p class="text-gray-400 text-xs mt-1.5">
                        Page: <span class="text-gray-300 font-medium">${source.pageNumber}</span>
                    </p>
                </div>
                <div class="flex-shrink-0">
                    <div class="bg-green-900 bg-opacity-50 border border-green-500 rounded-md px-2.5 py-1 text-center">
                        <span class="text-green-400 text-xs font-semibold">
                            ${source.confidence}%
                        </span>
                        <p class="text-green-400 text-xs">
                            match
                        </p>
                    </div>
                </div>
            </div>
            <div class="mt-3 bg-[#1e293b] rounded-lg p-3 border border-gray-700">
                <p class="text-gray-300 text-sm leading-relaxed line-clamp-3">
                    "${source.chunkText.substring(0, 220)}${source.chunkText.length > 220 ? '...' : ''}"
                </p>
            </div>
            <div class="mt-3 flex items-center justify-between">
                <span class="text-gray-500 text-xs">
                    Retrieved source
                </span>
                <a
                    href="${source.sourceUrl || '#'}"
                    target="_blank"
                    rel="noopener noreferrer"
                    class="text-cyan-400 hover:text-cyan-300 text-xs underline hover:no-underline transition-colors"
                >
                    View Source
                </a>
            </div>
        </div>
    `).join("");
}

function renderCitationResponse(answer, sources, confidenceScore = 0) {
    const normalizedSources = buildSourceCards(sources);
    const primarySource = Array.isArray(sources) && sources.length > 0
        ? normalizeSourceForUI(sources[0])
        : null;

    const primaryFilename = primarySource ? primarySource.filename : "Unknown Source";
    const primaryConfidence = Math.round(confidenceScore || primarySource?.confidence || 0);

    const wrapper = document.createElement("div");
    wrapper.className = "flex gap-4 fade-in";

    wrapper.innerHTML = `
        <div
            class="w-12 h-12 rounded-full bg-cyan-500 flex items-center justify-center font-bold">
            AI
        </div>

        <div
            class="chat-card bg-[#1e293b] border border-gray-700 rounded-2xl p-5 max-w-5xl">
            <div class="mb-3 pb-3 border-b border-gray-600">
                <div class="flex items-center justify-between gap-3">
                    <p class="text-cyan-400 font-semibold text-xs">📄 ${primaryFilename}</p>
                    <span class="text-green-400 text-xs font-semibold">${primaryConfidence}% confidence</span>
                </div>
            </div>

            <p class="leading-8 text-gray-200 whitespace-pre-line">
                ${answer}
            </p>

            ${normalizedSources}
        </div>
    `;

    chatSection.appendChild(wrapper);
    chatSection.scrollTop = chatSection.scrollHeight;
}

if (sendBtn) {
    sendBtn.addEventListener("click", async () => {

        const question = questionInput.value.trim();

        if (!question) return;

        sendBtn.disabled = true;
        sendBtn.textContent = "Searching...";

        addMessage(
            "USER",
            question
        );

        questionInput.value = "";

        addMessage(
            "AI",
            "Thinking..."
        );

        try {

            const response = await fetch(
                "http://127.0.0.1:8000/ask",
                {
                    method: "POST",

                    headers: {
                        "Content-Type": "application/json"
                    },

                    body: JSON.stringify({

                        question: question,

                        email: localStorage.getItem("email")
                    })
                }
            );

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();

            console.log(data);

            if (!data.answer) {
                throw new Error("Invalid response: no answer provided");
            }

            if (chatSection.lastElementChild) {
                chatSection.lastElementChild.remove();
            }

            renderCitationResponse(
                data.answer,
                data.sources || [],
                data.confidence_score || 0
            );

            saveCurrentChat(
                data.question,
                data.answer,
                data.sources || []
            );

            renderChatHistory();

        } catch (error) {

            console.log(error);

            if (chatSection.lastElementChild) {
                chatSection.lastElementChild.remove();
            }

            addMessage(
                "AI",
                `❌ Error: ${error.message || "Failed to generate response"}`
            );
        } finally {
            sendBtn.disabled = false;
            sendBtn.textContent = "Ask AI";
        }
    });
} else {
    console.error("Send button not found!");
}

// =========================================
// RENDER AI RESPONSE
// =========================================

function renderAIResponse(data) {
    renderCitationResponse(
        data.answer,
        data.sources || [],
        data.confidence_score || 0
    );
}
// =========================================
// PROFILE DROPDOWN
// =========================================

const profileBtn =
    document.getElementById("profileBtn");

const profileMenu =
    document.getElementById("profileMenu");

profileBtn.addEventListener("click", () => {

    profileMenu.classList.toggle("hidden");
});


// close dropdown when clicking outside

window.addEventListener("click", (e) => {

    if (
        !profileBtn.contains(e.target)
        &&
        !profileMenu.contains(e.target)
    ) {

        profileMenu.classList.add("hidden");
    }
});

// =========================================
// LOGOUT
// =========================================

const logoutBtn =
    document.getElementById("logoutBtn");

logoutBtn.addEventListener("click", () => {

    // remove token
    localStorage.removeItem("token");

    // redirect
    window.location.href =
        "home.html";
});

// =========================================
// EDIT PROFILE MODAL
// =========================================

const editProfileBtn =
    document.getElementById("editProfileBtn");

const editProfileModal =
    document.getElementById("editProfileModal");

const closeProfileModal =
    document.getElementById("closeProfileModal");

const editUsername =
    document.getElementById("editUsername");

const editEmail =
    document.getElementById("editEmail");


if (
    editProfileBtn &&
    editProfileModal
) {

    // OPEN MODAL

    editProfileBtn.addEventListener("click", () => {

        editProfileModal.classList.remove("hidden");

        editUsername.value =
            localStorage.getItem("username") || "";

        editEmail.value =
            localStorage.getItem("email") || "";
    });
}


// CLOSE BUTTON

if (closeProfileModal) {

    closeProfileModal.addEventListener("click", () => {

        editProfileModal.classList.add("hidden");
    });
}


// CLICK OUTSIDE

window.addEventListener("click", (e) => {

    if (e.target === editProfileModal) {

        editProfileModal.classList.add("hidden");
    }
});


// =========================================
// SAVE PROFILE CHANGES
// =========================================

const saveProfileBtn =
    document.getElementById("saveProfileBtn");

saveProfileBtn.addEventListener("click", async () => {

    const updatedUsername =
        editUsername.value;

    const updatedEmail =
        editEmail.value;

    const updatedPassword =
        document.getElementById("editPassword").value;


    // VALIDATION

    if (
        !updatedUsername ||
        !updatedEmail
    ) {

        alert("Username and email required");

        return;
    }

    try {

        const response = await fetch(
            "http://127.0.0.1:8000/update-profile",
            {
                method: "PUT",

                headers: {
                    "Content-Type": "application/json"
                },

                body: JSON.stringify({
                    username: updatedUsername,
                    email: updatedEmail,
                    password: updatedPassword
                })
            }
        );

        const data = await response.json();

        if (response.ok) {

            // UPDATE LOCAL STORAGE

            localStorage.setItem(
                "username",
                updatedUsername
            );

            localStorage.setItem(
                "email",
                updatedEmail
            );

            // UPDATE UI

            profileName.innerText =
                updatedUsername;

            profileEmail.innerText =
                updatedEmail;

            alert("Profile updated successfully");

            editProfileModal.classList.add("hidden");

        } else {

            alert(data.detail);
        }

    } catch (error) {

        console.log(error);

        alert("Something went wrong");
    }
});

// =========================================
// LOAD CHAT HISTORY
// =========================================

function renderChatHistory() {

    const historyContainer =
        document.getElementById(
            "historyContainer"
        );

    historyContainer.innerHTML = "";

    if (allChats.length === 0) {

        historyContainer.innerHTML = `

            <p class="text-sm text-gray-400">

                No recent chats

            </p>
        `;

        return;
    }

    allChats.forEach(chat => {

        const historyItem =
            document.createElement("div");

        historyItem.className =
            "bg-white border border-gray-200 rounded-2xl p-4 text-sm text-gray-700 hover:border-blue-400 transition-all cursor-pointer shadow-sm";

        historyItem.innerHTML = `

            <div class="flex items-center justify-between">

                <span class="truncate flex-1">

                    ${chat.title}

                </span>

                <button
                    class="deleteChatBtn text-red-500 hover:text-red-600 font-bold">

                    ✕

                </button>

            </div>
        `;

        historyItem.addEventListener(
            "click",
            () => {

                currentChatId = chat.id;

                chatSection.innerHTML = "";

                chat.messages.forEach(msg => {

                    addMessage(
                        "USER",
                        msg.question
                    );

                    renderCitationResponse(
                        msg.answer,
                        msg.sources || [],
                        msg.sources?.length > 0
                            ? Math.round(
                                msg.sources.reduce((sum, source) => sum + (Number(source.confidence) || 0), 0) / msg.sources.length
                            )
                            : 0
                    );
                });
            }
        );

        const deleteChatBtn =
            historyItem.querySelector(
                ".deleteChatBtn"
            );

        deleteChatBtn.addEventListener(
            "click",

            (e) => {

                e.stopPropagation();

                allChats = allChats.filter(
                    item => item.id !== chat.id
                );

                localStorage.setItem(

                    `allChats_${localStorage.getItem("email")}`,

                    JSON.stringify(allChats)
                );

                renderChatHistory();
            }
        );

        historyContainer.appendChild(
            historyItem
        );

    });
}


// LOAD ON PAGE START

renderChatHistory();

// =========================================
// NEW CHAT
// =========================================

const newChatBtn =
    document.getElementById("newChatBtn");

newChatBtn.addEventListener("click", () => {

    // CLEAR CHAT SECTION
    currentChatId = null;

    chatSection.innerHTML = `

        <!-- WELCOME -->

        <div class="bg-white border border-gray-200 rounded-2xl p-4 shadow-sm max-w-3xl">

            <div class="flex items-start gap-3">

                <div class="w-12 h-12 rounded-xl bg-blue-100 flex items-center justify-center flex-shrink-0">

                    <i data-lucide="bot" class="w-6 h-6 text-blue-600"></i>

                </div>

                <div>

                    <h2 class="text-xl font-semibold text-gray-800">

                        Welcome 👋

                    </h2>

                    <p class="text-gray-600 mt-2 leading-6 text-sm">

                        Upload documents and ask intelligent semantic questions using local AI.

                    </p>

                    <p class="text-gray-500 mt-1 text-sm">

                        I’m here to help you find answers from your documents.

                    </p>

                </div>

            </div>

        </div>
    `;

    lucide.createIcons();
});

const clearHistoryBtn =
    document.getElementById(
        "clearHistoryBtn"
    );
    
clearHistoryBtn.addEventListener(
    "click",

    () => {

        deleteMode = "chats";

        deleteAllModal.classList.remove(
            "hidden"
        );
    }
);

// =========================================
// LOAD UPLOADED FILES
// =========================================

async function loadUploadedFiles() {

    try {

        const email =
            localStorage.getItem("email");

        const response = await fetch(
            `http://127.0.0.1:8000/uploaded-files/${email}`
        );

        const data = await response.json();

        uploadedFilesContainer.innerHTML = "";

        data.forEach((file) => {

            const fileCard =
                document.createElement("div");

            fileCard.className =
                "bg-white border border-gray-200 rounded-2xl p-3 flex items-center justify-between gap-3 shadow-sm";

            fileCard.innerHTML = `

    <div class="flex items-center gap-3 flex-1 overflow-hidden">

        <div class="w-10 h-10 rounded-xl bg-blue-100 flex items-center justify-center">

            <i data-lucide="file-text"
                class="w-5 h-5 text-blue-600"></i>

        </div>

        <div class="overflow-hidden flex-1">

            <p class="text-sm font-medium text-gray-700 truncate">

                ${file.filename}

            </p>

        </div>

    </div>

    <div class="flex items-center gap-3">

        <!-- PREVIEW -->

        <button
            class="previewFileBtn text-blue-500 hover:text-blue-600 text-sm">

            👁
        </button>

        <!-- DOWNLOAD -->

        <button
            class="downloadFileBtn text-green-500 hover:text-green-600 text-sm">

            ⬇
        </button>

        <!-- DELETE -->

        <button
            class="deleteFileBtn text-red-500 hover:text-red-600 text-sm">

            ✕
        </button>

    </div>
`;

            // DELETE FILE

            const deleteBtn =
                fileCard.querySelector(
                    ".deleteFileBtn"
                );



            deleteBtn.addEventListener("click", async () => {

                try {

                    await fetch(
                        `http://127.0.0.1:8000/delete-file/${file.id}`,
                        {
                            method: "DELETE"
                        }
                    );

                    loadUploadedFiles();

                } catch (error) {

                    console.log(error);
                }
            });

            // =========================================
            // PREVIEW FILE
            // =========================================

            const previewBtn =
                fileCard.querySelector(
                    ".previewFileBtn"
                );

            previewBtn.addEventListener("click", () => {

                const previewUrl =
                    `http://127.0.0.1:8000/${file.filepath}`;

                window.open(
                    previewUrl,
                    "_blank"
                );
            });

            // =========================================
            // DOWNLOAD FILE
            // =========================================

            const downloadBtn =
                fileCard.querySelector(
                    ".downloadFileBtn"
                );

            downloadBtn.addEventListener("click", async () => {

                const response = await fetch(
                    `http://127.0.0.1:8000/${file.filepath}`
                );

                const blob = await response.blob();

                const blobUrl =
                    window.URL.createObjectURL(blob);

                const link =
                    document.createElement("a");

                link.href = blobUrl;

                link.download = file.filename;

                document.body.appendChild(link);

                link.click();

                document.body.removeChild(link);

                window.URL.revokeObjectURL(blobUrl);
            });

            uploadedFilesContainer.appendChild(
                fileCard
            );
        });

        fileCount.innerText =
            `${data.length} Files`;

        lucide.createIcons();

    } catch (error) {

        console.log(error);
    }
}

loadUploadedFiles();

// =========================================
// CLEAR ALL FILES
// =========================================

const clearAllFilesBtn =
    document.getElementById(
        "clearAllFilesBtn"
    );

// =========================================
// DELETE ALL FILES MODAL
// =========================================

const deleteAllModal =
    document.getElementById(
        "deleteAllModal"
    );

const cancelDeleteBtn =
    document.getElementById(
        "cancelDeleteBtn"
    );

const confirmDeleteBtn =
    document.getElementById(
        "confirmDeleteBtn"
    );

let deleteMode = null;

// OPEN MODAL

clearAllFilesBtn.addEventListener("click", () => {

    deleteMode = "files";

    deleteAllModal.classList.remove(
        "hidden"
    );
});


// CANCEL

cancelDeleteBtn.addEventListener("click", () => {

    deleteAllModal.classList.add(
        "hidden"
    );
});


// CLICK OUTSIDE

window.addEventListener("click", (e) => {

    if (e.target === deleteAllModal) {

        deleteAllModal.classList.add(
            "hidden"
        );
    }
});


// CONFIRM DELETE


confirmDeleteBtn.addEventListener("click", async () => {

    try {

        if (deleteMode === "files") {

            await fetch(
                "http://127.0.0.1:8000/delete-all-files",
                {
                    method: "DELETE"
                }
            );

            loadUploadedFiles();
        }

        else if (deleteMode === "chats") {

            const email =
                localStorage.getItem(
                    "email"
                );

            localStorage.removeItem(
                `allChats_${email}`
            );

            allChats = [];

            currentChatId = null;

            renderChatHistory();

            chatSection.innerHTML = "";
        }

        deleteAllModal.classList.add(
            "hidden"
        );

        deleteMode = null;

    } catch (error) {

        console.log(error);
    }
});