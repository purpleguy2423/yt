let player;

function onYouTubeIframeAPIReady() {
    // This function will be called when the API is ready
    console.log('YouTube API Ready');
}

// Video download functionality
let downloadModal;

// Initialize modals and toasts when document is ready
document.addEventListener('DOMContentLoaded', function() {
    // Initialize download modal if not already defined in download_modal.html
    if (typeof downloadModal === 'undefined') {
        const modalEl = document.getElementById('downloadModal');
        if (modalEl) {
            downloadModal = new bootstrap.Modal(modalEl);
        }
    }
});

// Function to open download modal and fetch download options
function openDownloadModal(videoId) {
    // Safe version of getting elements with fallback
    const getElementSafe = (id) => {
        const element = document.getElementById(id);
        if (!element) {
            console.error(`Element not found: #${id}`);
            return null;
        }
        return element;
    };
    
    // Get elements
    const downloadModalEl = getElementSafe('downloadModal');
    
    // If modal element doesn't exist, show a notification toast and return
    if (!downloadModalEl) {
        console.error("Download modal not found in the DOM");
        
        // Create a notification toast
        const toastEl = document.createElement('div');
        toastEl.className = 'toast align-items-center text-white bg-danger border-0 position-fixed bottom-0 end-0 m-3';
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    <strong>Error:</strong> Download feature is not available on this page. Please go to the home page to use this feature.
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        document.body.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
        toast.show();
        
        // Remove the element after it's hidden
        toastEl.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toastEl);
        });
        
        return;
    }
    
    // Get the rest of the elements
    const downloadLoading = getElementSafe('downloadLoading');
    const downloadContent = getElementSafe('downloadContent');
    const downloadError = getElementSafe('downloadError');
    const videoStreamsList = getElementSafe('videoStreamsList');
    const audioStreamsList = getElementSafe('audioStreamsList');
    
    // Check if we have all required elements
    if (!downloadLoading || !downloadContent || !downloadError || !videoStreamsList || !audioStreamsList) {
        console.error("Missing required elements for download modal");
        return;
    }
    
    // Reset modal state
    downloadLoading.classList.remove('d-none');
    downloadContent.classList.add('d-none');
    downloadError.classList.add('d-none');
    downloadModalEl.setAttribute('data-video-id', videoId);
    
    // Show modal
    if (typeof downloadModal !== 'undefined' && downloadModal) {
        downloadModal.show();
    } else {
        // Initialize modal if not already done
        window.downloadModal = new bootstrap.Modal(downloadModalEl);
        window.downloadModal.show();
    }
    
    // Fetch download options from server
    fetch(`/video/download-options/${videoId}`)
        .then(response => response.json())
        .then(data => {
            // Hide loading indicator
            downloadLoading.classList.add('d-none');
            
            if (!data.success) {
                // Show error
                downloadError.textContent = data.error || 'Failed to load download options';
                downloadError.classList.remove('d-none');
                return;
            }
            
            // Set video details safely
            const downloadTitle = getElementSafe('downloadTitle');
            const downloadAuthor = getElementSafe('downloadAuthor');
            const downloadThumbnail = getElementSafe('downloadThumbnail');
            const downloadLength = getElementSafe('downloadLength');
            
            if (downloadTitle) downloadTitle.textContent = data.title;
            if (downloadAuthor) downloadAuthor.textContent = `By: ${data.author}`;
            if (downloadThumbnail) downloadThumbnail.src = data.thumbnail;
            
            // Format video length
            if (downloadLength) {
                const minutes = Math.floor(data.length / 60);
                const seconds = data.length % 60;
                downloadLength.textContent = `Length: ${minutes}:${seconds.toString().padStart(2, '0')}`;
            }
            
            // Create video streams list
            let videoStreamsHTML = '';
            if (data.video_streams && data.video_streams.length > 0) {
                videoStreamsHTML = data.video_streams.map(stream => `
                    <button type="button" 
                            class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" 
                            onclick="downloadStream('${videoId}', ${stream.itag})">
                        ${stream.resolution} (${stream.mime_type.split('/')[1]})
                        <span class="badge bg-primary rounded-pill">${stream.size_mb} MB</span>
                    </button>
                `).join('');
            } else {
                videoStreamsHTML = '<div class="list-group-item">No video streams available</div>';
            }
            videoStreamsList.innerHTML = videoStreamsHTML;
            
            // Create audio streams list
            let audioStreamsHTML = '';
            if (data.audio_streams && data.audio_streams.length > 0) {
                audioStreamsHTML = data.audio_streams.map(stream => `
                    <button type="button" 
                            class="list-group-item list-group-item-action d-flex justify-content-between align-items-center" 
                            onclick="downloadStream('${videoId}', ${stream.itag})">
                        ${stream.abr} (${stream.mime_type.split('/')[1]})
                        <span class="badge bg-primary rounded-pill">${stream.size_mb} MB</span>
                    </button>
                `).join('');
            } else {
                audioStreamsHTML = '<div class="list-group-item">No audio streams available</div>';
            }
            audioStreamsList.innerHTML = audioStreamsHTML;
            
            // Show content
            downloadContent.classList.remove('d-none');
        })
        .catch(error => {
            // Hide loading indicator and show error
            if (downloadLoading) downloadLoading.classList.add('d-none');
            if (downloadError) {
                downloadError.textContent = `Error: ${error.message}`;
                downloadError.classList.remove('d-none');
            }
        });
}

// Function to download a specific stream
function downloadStream(videoId, itag) {
    // Safe version of getting elements with fallback
    const getElementSafe = (id) => {
        const element = document.getElementById(id);
        if (!element) {
            console.error(`Element not found: #${id}`);
            return null;
        }
        return element;
    };
    
    // Get elements
    const downloadLoading = getElementSafe('downloadLoading');
    const downloadContent = getElementSafe('downloadContent');
    const downloadError = getElementSafe('downloadError');
    
    // Check if we have all required elements
    if (!downloadLoading || !downloadContent || !downloadError) {
        console.error("Missing required elements for download stream");
        return;
    }
    
    // Show loading state
    downloadContent.classList.add('d-none');
    downloadLoading.classList.remove('d-none');
    downloadError.classList.add('d-none');
    
    // Start download
    fetch(`/video/download/${videoId}?itag=${itag}`)
        .then(response => response.json())
        .then(data => {
            // Hide loading
            downloadLoading.classList.add('d-none');
            
            if (!data.success) {
                // Show error
                downloadError.textContent = data.error || 'Download failed';
                downloadError.classList.remove('d-none');
                return;
            }
            
            // Close modal if it exists
            if (typeof downloadModal !== 'undefined' && downloadModal) {
                downloadModal.hide();
            }
            
            // Instead of toast, show success directly in the modal
            document.getElementById('downloadProgress').classList.add('d-none');
            
            // Get the success element and update it
            const downloadSuccess = document.getElementById('downloadSuccess');
            if (downloadSuccess) {
                downloadSuccess.classList.remove('d-none');
                
                // Update download link
                const downloadLink = document.getElementById('downloadLink');
                if (downloadLink) {
                    downloadLink.href = '/' + data.file_path;
                    downloadLink.download = data.file_path.split('/').pop();
                }
            } else {
                // If success element doesn't exist, show a notification toast
                const toastEl = document.createElement('div');
                toastEl.className = 'toast align-items-center text-white bg-success border-0 position-fixed bottom-0 end-0 m-3';
                toastEl.setAttribute('role', 'alert');
                toastEl.setAttribute('aria-live', 'assertive');
                toastEl.setAttribute('aria-atomic', 'true');
                
                const note = data.note ? `<br><small class="text-light">${data.note}</small>` : '';
                
                toastEl.innerHTML = `
                    <div class="d-flex">
                        <div class="toast-body">
                            <strong>Download Ready:</strong> ${data.title}${note}
                        </div>
                        <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                    </div>
                `;
                
                document.body.appendChild(toastEl);
                const toast = new bootstrap.Toast(toastEl, { delay: 5000 });
                toast.show();
                
                // Remove the element after it's hidden
                toastEl.addEventListener('hidden.bs.toast', () => {
                    document.body.removeChild(toastEl);
                });
            }
        })
        .catch(error => {
            // Hide loading and show error
            downloadLoading.classList.add('d-none');
            downloadError.textContent = `Error: ${error.message}`;
            downloadError.classList.remove('d-none');
        });
}

// Play video function using privacy-enhanced mode
// Function to save video to user collection
function saveVideo(videoId, title, thumbnail) {
    fetch(`/save-video/${videoId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            title: title,
            thumbnail: thumbnail,
        }),
    })
    .then(response => response.json())
    .then(data => {
        // Create toast notification
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white ${data.success ? 'bg-success' : 'bg-warning'} border-0 position-fixed bottom-0 end-0 m-3`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">
                    ${data.message}
                </div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
            </div>
        `;
        
        document.body.appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl, { delay: 3000 });
        toast.show();
        
        // Remove the element after it's hidden
        toastEl.addEventListener('hidden.bs.toast', () => {
            document.body.removeChild(toastEl);
        });
    })
    .catch(error => {
        console.error('Error:', error);
    });
}

function playVideo(videoId) {
    const videoPlayer = document.getElementById('videoPlayer');
    if (!videoPlayer) return;

    // Show channel loading if we're on the channel page
    const channelLoadingSpinner = document.getElementById('channelLoadingSpinner');
    if (channelLoadingSpinner && typeof window.showChannelLoading === 'function') {
        window.showChannelLoading();
        
        // Hide channel loading after a slight delay to simulate loading
        setTimeout(() => {
            if (typeof window.hideChannelLoading === 'function') {
                window.hideChannelLoading();
            }
        }, 800);
    }

    videoPlayer.classList.remove('d-none');

    // Find video details from available data
    let videoTitle = '';
    let videoThumbnail = '';
    const searchResultsContainer = document.getElementById('searchResults');
    
    if (searchResultsContainer) {
        const videoElement = searchResultsContainer.querySelector(`[data-video-id="${videoId}"]`);
        if (videoElement) {
            videoTitle = videoElement.getAttribute('data-title') || '';
            videoThumbnail = videoElement.getAttribute('data-thumbnail') || '';
        }
    }

    // Create the video container HTML with privacy-enhanced mode, download button, and save button
    const isLoggedIn = document.body.hasAttribute('data-user-logged-in') || false;
    
    let actionButtons = `
        <button type="button" class="btn btn-sm btn-outline-success me-2" onclick="openDownloadModal('${videoId}')">
            <i class="bi bi-download"></i> Download
        </button>
    `;
    
    // Add save button if user is logged in
    if (isLoggedIn) {
        actionButtons += `
            <button type="button" class="btn btn-sm btn-outline-primary" 
                    onclick="saveVideo('${videoId}', '${videoTitle.replace(/'/g, "\\'")}', '${videoThumbnail.replace(/'/g, "\\'")}')">
                <i class="bi bi-bookmark-plus"></i> Save to My Videos
            </button>
        `;
    }

    videoPlayer.innerHTML = `
        <div class="col-12">
            <div class="card">
                <div class="card-body">
                    <div class="d-flex justify-content-end mb-2">
                        ${actionButtons}
                    </div>
                    <div class="video-container">
                        <iframe
                            width="100%"
                            height="100%"
                            src="https://www.youtube-nocookie.com/embed/${videoId}?autoplay=1&rel=0&modestbranding=1&widget_referrer=youtube_proxy"
                            frameborder="0"
                            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                            allowfullscreen
                        ></iframe>
                    </div>
                </div>
            </div>
        </div>
    `;

    videoPlayer.scrollIntoView({ behavior: 'smooth' });
}

// Format view count
function formatViews(viewsStr) {
    const views = parseInt(viewsStr.replace(/[^0-9]/g, ''));
    if (isNaN(views)) return viewsStr;
    if (views >= 1000000) return `${(views/1000000).toFixed(1)}M views`;
    if (views >= 1000) return `${(views/1000).toFixed(1)}K views`;
    return `${views} views`;
}

// Initialize search functionality only on index page
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on the search page
    const searchForm = document.getElementById('searchForm');
    
    // Handle channel page functionality
    const channelVideos = document.getElementById('channelVideos');
    if (channelVideos) {
        console.log('Channel page loaded');
        
        // Initialize channel page loading functionality
        const channelLoadingSpinner = document.getElementById('channelLoadingSpinner');
        if (channelLoadingSpinner) {
            const loadingQuote = channelLoadingSpinner.querySelector('.loading-quote');
            // Set a random quote if loading is shown
            if (loadingQuote) {
                const channelQuotes = [
                    "Finding the best videos from this creator...",
                    "Organizing this channel's content for you...",
                    "Creator's videos incoming...",
                    "Quality content from this channel on the way...",
                    "Gathering video highlights from this creator..."
                ];
                const randomQuote = channelQuotes[Math.floor(Math.random() * channelQuotes.length)];
                loadingQuote.textContent = randomQuote;
            }
        }
        
        // Function to show channel loading spinner
        window.showChannelLoading = function() {
            if (channelLoadingSpinner) {
                channelLoadingSpinner.classList.remove('d-none');
                channelVideos.style.opacity = '0.3';
            }
        };
        
        // Function to hide channel loading spinner
        window.hideChannelLoading = function() {
            if (channelLoadingSpinner) {
                channelLoadingSpinner.classList.add('d-none');
                channelVideos.style.opacity = '1';
            }
        };
        
        return; // Exit early if on channel page
    }
    
    // Exit if not on search page and not on channel page
    if (!searchForm) return;

    const searchInput = document.getElementById('searchInput');
    const searchResults = document.getElementById('searchResults');
    const loadingSpinner = document.getElementById('loadingSpinner');
    const videoPlayer = document.getElementById('videoPlayer');

    // Loading screen quotes
    const loadingQuotes = [
        "Great videos take time to find, just like hidden treasures.",
        "Discovering creators who match your interests...",
        "The internet is vast, finding the gems just for you...",
        "Traversing the YouTube universe to find what you're looking for...",
        "Sifting through pixels to find perfect content...",
        "Connecting you with creators who speak your language...",
        "Some videos are worth waiting for...",
        "Quality content incoming...",
        "Finding videos that will brighten your day...",
        "Searching for content that matches your interests..."
    ];

    // Show personalized loading spinner
    function showLoading() {
        const loadingContainer = loadingSpinner.querySelector('.loading-container');
        const loadingMessage = loadingSpinner.querySelector('.loading-message');
        const loadingQuote = loadingSpinner.querySelector('.loading-quote');
        
        // Set loading message based on search type
        if (currentSearchType === 'channels') {
            loadingContainer.className = 'loading-container channel-loading';
            loadingMessage.textContent = 'Discovering YouTube creators...';
        } else {
            loadingContainer.className = 'loading-container video-loading';
            loadingMessage.textContent = 'Searching for videos...';
        }
        
        // Random loading quote
        const randomQuote = loadingQuotes[Math.floor(Math.random() * loadingQuotes.length)];
        loadingQuote.textContent = randomQuote;
        
        // Show the loading spinner with animation
        loadingSpinner.classList.remove('d-none');
        searchResults.innerHTML = '';
    }

    // Hide loading spinner
    function hideLoading() {
        loadingSpinner.classList.add('d-none');
    }

    // Display error message
    function showError(message) {
        searchResults.innerHTML = `
            <div class="col-12">
                <div class="alert alert-danger" role="alert">
                    ${message}
                </div>
            </div>
        `;
    }

    // Add a search type toggle to the form
    if (!document.getElementById('searchTypeToggle')) {
        const searchTypeHTML = `
            <div class="form-check form-switch mb-3">
                <input class="form-check-input" type="checkbox" id="searchTypeToggle">
                <label class="form-check-label" for="searchTypeToggle">
                    <span id="searchTypeLabel">Search by: Channels</span>
                </label>
            </div>
        `;
        searchForm.insertAdjacentHTML('afterbegin', searchTypeHTML);
    }
    
    // Set default search type
    let currentSearchType = 'channels'; // Default to search for channels
    
    // Initialize toggle
    const searchTypeToggle = document.getElementById('searchTypeToggle');
    const searchTypeLabel = document.getElementById('searchTypeLabel');
    
    // Check if focus_channels parameter exists or we came from a channel page
    const checkUrlParameters = () => {
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.has('focus_channels') || 
            window.location.pathname.includes('/channel') || 
            searchInput.hasAttribute('data-focus-channels')) {
            
            searchTypeToggle.checked = false; // Keep it on channels mode
            currentSearchType = 'channels';
            searchTypeLabel.textContent = 'Search by: Channels';
            searchInput.placeholder = "Search for YouTube channels...";
        }
    };
    
    // Run check on page load
    checkUrlParameters();
    
    // Update search placeholder
    searchInput.placeholder = "Search for YouTube channels...";
    
    // Handle toggle changes
    searchTypeToggle.addEventListener('change', function() {
        currentSearchType = this.checked ? 'videos' : 'channels';
        searchTypeLabel.textContent = `Search by: ${this.checked ? 'Videos' : 'Channels'}`;
        searchInput.placeholder = this.checked 
            ? "Search for videos..." 
            : "Search for YouTube channels...";
    });
    
    // Handle search form submission
    searchForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const query = searchInput.value.trim();

        if (!query) return;

        showLoading();
        if (videoPlayer) {
            videoPlayer.classList.add('d-none');
        }

        try {
            const response = await fetch(`/search?q=${encodeURIComponent(query)}&type=${currentSearchType}`);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Search failed');
            }

            if (data.search_type === 'channels' && data.channels) {
                displayChannelResults(data.channels, data.total_results);
            } else if (data.search_type === 'videos' && data.results) {
                displaySearchResults(data.results, data.total_results);
            } else {
                showError('No results found for your search.');
            }
        } catch (error) {
            showError(error.message);
        } finally {
            hideLoading();
        }
    });

    // Display search results with enhanced channel information
    function displaySearchResults(results, totalResults) {
        if (results.length === 0) {
            searchResults.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-info" role="alert">
                        No videos found. Try a different search term.
                    </div>
                </div>
            `;
            return;
        }
        
        let resultsHTML = `
            <div class="col-12 mb-3">
                <div class="d-flex justify-content-between align-items-center">
                    <h3>Search Results</h3>
                    <span class="badge bg-secondary">${results.length} of ${totalResults || results.length} videos found</span>
                </div>
            </div>
        `;
        
        // Add message for more results if available
        if (totalResults > results.length) {
            resultsHTML += `
                <div class="col-12 mb-3">
                    <div class="alert alert-info small" role="alert">
                        <i class="bi bi-info-circle"></i> 
                        Showing ${results.length} of ${totalResults} total videos. YouTube limits how many results we can fetch at once.
                    </div>
                </div>
            `;
        }
        
        searchResults.innerHTML = resultsHTML + results.map(video => `
            <div class="col-md-4 mb-4">
                <div class="card h-100">
                    <div class="search-result" 
                         onclick="playVideo('${video.id}')"
                         data-video-id="${video.id}"
                         data-title="${video.title.replace(/"/g, '&quot;')}"
                         data-thumbnail="${video.thumbnail.replace(/"/g, '&quot;')}">
                        <div class="thumbnail-container">
                            <img src="${video.thumbnail}" class="card-img-top" alt="${video.title}"
                                 onerror="this.src='https://via.placeholder.com/480x360.png?text=Thumbnail+Unavailable'">
                            <span class="duration-badge">${video.duration}</span>
                        </div>
                        <div class="card-body">
                            <h5 class="card-title text-truncate" title="${video.title}">${video.title}</h5>
                            <p class="card-text description text-muted small">
                                ${video.description || 'No description available'}
                            </p>
                        </div>
                    </div>
                    <div class="card-footer bg-transparent border-top-0">
                        <a href="${video.channel_id ? `/channel/${video.channel_id}` : '#'}" 
                           class="channel-link" 
                           title="Visit channel"
                           ${!video.channel_id ? 'disabled' : ''}
                           onclick="event.stopPropagation(); ${!video.channel_id ? 'return false' : ''}">
                            <small class="text-muted">
                                <i class="bi bi-person-circle"></i> ${video.channel}
                            </small>
                        </a>
                        <div class="video-meta">
                            <small class="text-muted d-block">
                                <i class="bi bi-eye"></i> ${formatViews(video.views)}
                            </small>
                            <small class="text-muted d-block">
                                <i class="bi bi-clock"></i> ${video.publish_time}
                            </small>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }
    
    // Display channel search results
    function displayChannelResults(channels, totalResults) {
        if (channels.length === 0) {
            searchResults.innerHTML = `
                <div class="col-12">
                    <div class="alert alert-info" role="alert">
                        No channels found. Try a different search term.
                    </div>
                </div>
            `;
            return;
        }
        
        let resultsHTML = `
            <div class="col-12 mb-3">
                <div class="d-flex justify-content-between align-items-center">
                    <h3>Channel Results</h3>
                    <span class="badge bg-secondary">${channels.length} of ${totalResults || channels.length} channels found</span>
                </div>
            </div>
        `;
        
        // Add message for more results if available
        if (totalResults > channels.length) {
            resultsHTML += `
                <div class="col-12 mb-3">
                    <div class="alert alert-info small" role="alert">
                        <i class="bi bi-info-circle"></i> 
                        Showing ${channels.length} of ${totalResults} total channels. YouTube limits how many results we can fetch at once.
                    </div>
                </div>
            `;
        }
        
        searchResults.innerHTML = resultsHTML + channels.map(channel => `
            <div class="col-md-4 mb-4">
                <div class="card h-100">
                    <div class="channel-result">
                        <div class="channel-image-container text-center mt-3">
                            <img src="${channel.thumbnail || 'https://via.placeholder.com/100x100.png?text=Channel'}" 
                                 class="channel-image rounded-circle" alt="${channel.name}"
                                 onerror="this.src='https://via.placeholder.com/100x100.png?text=Channel'">
                        </div>
                        <div class="card-body text-center">
                            <h5 class="card-title">${channel.name}</h5>
                            <p class="card-text text-muted small">
                                ${channel.subscriber_count || 'Subscriber count unavailable'}
                            </p>
                            <p class="card-text description text-muted small">
                                ${channel.description || 'No description available'}
                            </p>
                            <a href="/channel/${channel.id}" class="btn btn-primary btn-sm mt-2">View Channel</a>
                        </div>
                    </div>
                </div>
            </div>
        `).join('');
    }
});