/* ═══════════════════════════════════════════════════════════════════════
   FoodieAI — Application Logic Orchestrator (app.js)
   ═══════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', async () => {
  // --- DOM Elements ---
  const healthBadge = document.getElementById('health-badge');
  const locationToggle = document.getElementById('location-toggle');
  const locationText = document.getElementById('selected-location-text');
  const locationMenu = document.getElementById('location-menu');
  const locationSearch = document.getElementById('location-search');
  const locationOptions = document.getElementById('location-options');
  const locationError = document.getElementById('location-validation-error');
  
  const cuisineInput = document.getElementById('cuisine-input');
  const cuisineMenu = document.getElementById('cuisine-menu');
  
  const budgetButtons = document.querySelectorAll('.budget-btn');
  const ratingSlider = document.getElementById('rating-slider');
  const ratingValue = document.getElementById('rating-value');
  const ratingStarsTrack = document.getElementById('rating-stars-track');
  
  const preferencesText = document.getElementById('preferences-text');
  const charCounter = document.getElementById('char-counter');
  
  const submitBtn = document.getElementById('submit-btn');
  const submitText = document.getElementById('submit-btn-text');
  const submitIcon = document.getElementById('submit-btn-icon');
  
  const resultsContainer = document.getElementById('results-container');
  const resultsArea = document.getElementById('results-area');
  const metadataContainer = document.getElementById('metadata-container');
  const newSearchBtn = document.getElementById('new-search-btn');
  const clearSearchBtnHeader = document.getElementById('clear-search-btn-header');
  
  // --- State Variables ---
  let selectedLocation = '';
  let selectedBudget = 'medium'; // default matches template active button
  let availableLocations = [];
  let availableCuisines = [];
  
  // --- 1. System Health Check & Dynamic Data Initialization ---
  try {
    const health = await window.FoodieApi.checkHealth();
    if (health.status === 'healthy') {
      healthBadge.innerHTML = `<span class="material-symbols-outlined text-[16px] text-secondary">auto_awesome</span> AI Concierge Active`;
      healthBadge.className = "hidden lg:flex items-center gap-2 px-3 py-1.5 glass-panel rounded-full text-xs text-secondary-fixed font-medium";
    }
  } catch (err) {
    console.warn("Backend degraded or unreachable:", err);
    healthBadge.innerHTML = `<span class="material-symbols-outlined text-[16px] text-error">warning</span> Offline Mode`;
    healthBadge.className = "hidden lg:flex items-center gap-2 px-3 py-1.5 glass-panel rounded-full text-xs text-error font-medium";
  }

  // Load datasets to populate fields
  try {
    const [locations, cuisines] = await Promise.all([
      window.FoodieApi.fetchLocations(),
      window.FoodieApi.fetchCuisines()
    ]);
    availableLocations = locations;
    availableCuisines = cuisines;
    
    // Initialize custom dropdown option nodes
    populateLocationOptions(availableLocations);
  } catch (err) {
    console.error("Failed to fetch initial dropdown data:", err);
  }

  // --- 2. Custom Location Searchable Dropdown Logic ---
  locationToggle.addEventListener('click', (e) => {
    e.stopPropagation();
    locationMenu.classList.toggle('show');
    locationToggle.classList.toggle('open');
    if (locationMenu.classList.contains('show')) {
      locationSearch.focus();
    }
  });

  locationSearch.addEventListener('input', (e) => {
    const filter = e.target.value.toLowerCase().trim();
    const filtered = availableLocations.filter(loc => loc.toLowerCase().includes(filter));
    populateLocationOptions(filtered);
  });

  locationSearch.addEventListener('click', (e) => {
    e.stopPropagation(); // Avoid closing dropdown when typing in search input
  });

  // Close dropdown menu when clicking outside
  document.addEventListener('click', () => {
    locationMenu.classList.remove('show');
    locationToggle.classList.remove('open');
    cuisineMenu.classList.remove('show');
  });

  function populateLocationOptions(list) {
    locationOptions.innerHTML = '';
    
    if (list.length === 0) {
      locationOptions.innerHTML = `<div class="dropdown-empty">No locations match your search</div>`;
      return;
    }
    
    list.forEach(loc => {
      const option = document.createElement('div');
      option.className = `dropdown-option ${loc === selectedLocation ? 'selected' : ''}`;
      option.textContent = loc;
      option.addEventListener('click', (e) => {
        e.stopPropagation();
        selectedLocation = loc;
        locationText.textContent = loc;
        locationError.classList.remove('show');
        locationToggle.parentNode.parentNode.classList.remove('invalid');
        locationMenu.classList.remove('show');
        locationToggle.classList.remove('open');
      });
      locationOptions.appendChild(option);
    });
  }

  // --- 3. Cuisine Autocomplete Suggestions Logic ---
  cuisineInput.addEventListener('input', (e) => {
    const val = e.target.value.toLowerCase().trim();
    cuisineMenu.innerHTML = '';
    
    if (val.length < 1) {
      cuisineMenu.classList.remove('show');
      return;
    }
    
    // Filter matching cuisines
    const matches = availableCuisines.filter(c => c.toLowerCase().startsWith(val)).slice(0, 8);
    
    if (matches.length === 0) {
      cuisineMenu.classList.remove('show');
      return;
    }
    
    matches.forEach(m => {
      const option = document.createElement('div');
      option.className = 'autocomplete-option';
      option.textContent = m;
      option.addEventListener('click', (e) => {
        e.stopPropagation();
        cuisineInput.value = m;
        cuisineMenu.classList.remove('show');
      });
      cuisineMenu.appendChild(option);
    });
    
    cuisineMenu.classList.add('show');
  });

  cuisineInput.addEventListener('click', (e) => {
    e.stopPropagation();
    if (cuisineMenu.children.length > 0 && cuisineInput.value.length > 0) {
      cuisineMenu.classList.add('show');
    }
  });

  // --- 4. Budget Toggles Logic ---
  budgetButtons.forEach(btn => {
    btn.addEventListener('click', () => {
      budgetButtons.forEach(b => {
        b.className = "budget-btn";
      });
      btn.className = "budget-btn active";
      selectedBudget = btn.dataset.budget;
    });
  });

  // --- 5. Star Rating Slider Display Logic ---
  ratingSlider.addEventListener('input', (e) => {
    const rating = parseFloat(e.target.value).toFixed(1);
    ratingValue.textContent = `${rating}+`;
    
    // Dynamically adjust star highlight style
    if (rating >= 4.5) {
      ratingValue.className = "rating-value high animate-pulse-glow";
    } else {
      ratingValue.className = "rating-value";
    }
    
    // Update floating stars visibility/track style
    const stars = ratingStarsTrack.querySelectorAll('.material-symbols-outlined');
    const roundedInt = Math.floor(rating);
    stars.forEach((star, index) => {
      if (index < roundedInt) {
        star.style.opacity = '1';
        star.style.fontVariationSettings = "'FILL' 1";
      } else if (index === roundedInt && rating % 1 >= 0.5) {
        star.style.opacity = '0.7';
        star.style.fontVariationSettings = "'FILL' 0";
      } else {
        star.style.opacity = '0.35';
        star.style.fontVariationSettings = "'FILL' 0";
      }
    });
  });

  // Trigger initial track updates
  ratingSlider.dispatchEvent(new Event('input'));

  // --- 6. Specific Preferences Character Counter ---
  preferencesText.addEventListener('input', (e) => {
    const len = e.target.value.length;
    charCounter.textContent = `${len} / 500`;
  });

  // --- 7. Form Submission Handler ---
  submitBtn.addEventListener('click', async (e) => {
    e.preventDefault();
    
    // Form Validation
    if (!selectedLocation) {
      locationError.classList.add('show');
      locationToggle.parentNode.parentNode.classList.add('invalid');
      
      // Form Shake Animation
      const form = document.querySelector('form');
      form.classList.add('animate-shake');
      setTimeout(() => {
        form.classList.remove('animate-shake');
      }, 400);
      return;
    }
    
    // Request State Transition
    setLoadingState(true);
    resultsContainer.classList.add('hidden');
    
    const payload = {
      location: selectedLocation,
      budget: selectedBudget,
      cuisine: cuisineInput.value.trim() || null,
      min_rating: parseFloat(ratingSlider.value),
      additional_preferences: preferencesText.value.trim() || null
    };

    try {
      const response = await window.FoodieApi.fetchRecommendations(payload);
      
      if (response.success && response.recommendations && response.recommendations.length > 0) {
        renderResults(response);
        setLoadingState(false);
        resultsContainer.classList.remove('hidden');
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
      } else {
        // No results state
        renderNoResultsState(response.message || "No matching restaurants found.");
        setLoadingState(false);
        resultsContainer.classList.remove('hidden');
        resultsContainer.scrollIntoView({ behavior: 'smooth' });
      }
    } catch (err) {
      console.error(err);
      renderErrorBox(err.message || "An error occurred while contacting the AI concierge.");
      setLoadingState(false);
      resultsContainer.classList.remove('hidden');
      resultsContainer.scrollIntoView({ behavior: 'smooth' });
    }
  });

  // --- Loading State Handler ---
  function setLoadingState(isLoading) {
    if (isLoading) {
      submitBtn.disabled = true;
      submitText.textContent = "Plating recommendations...";
      submitIcon.textContent = "restaurant";
      submitIcon.className = "material-symbols-outlined animate-float";
      
      // Render animated skeleton loaders in results wrapper
      resultsArea.innerHTML = window.FoodieComponents.renderSkeletonCards(3);
      metadataContainer.innerHTML = `<span class="loading-text">Preparing curated matches...</span>`;
    } else {
      submitBtn.disabled = false;
      submitText.textContent = "Get Recommendations";
      submitIcon.textContent = "auto_awesome";
      submitIcon.className = "material-symbols-outlined";
    }
  }

  // --- Dynamic Results Rendering ---
  function renderResults(data) {
    resultsArea.innerHTML = '';
    
    // Populate Metadata Bar
    metadataContainer.innerHTML = window.FoodieComponents.renderMetadataBar(
      data.filter_metadata,
      data.response_time_ms,
      data.model_used
    );
    
    const recs = data.recommendations;
    
    // Top Ranked Featured Match (#1)
    const featuredHtml = window.FoodieComponents.renderFeaturedCard(recs[0], 1);
    resultsArea.insertAdjacentHTML('beforeend', featuredHtml);
    
    // Grid of standard cards (#2 to #5)
    if (recs.length > 1) {
      let gridHtml = '<div class="results-grid">';
      for (let i = 1; i < recs.length; i++) {
        // Stagger indexing starts from stagger-4 for sub-grid
        const staggerIndex = i + 3 > 6 ? 6 : i + 3;
        gridHtml += window.FoodieComponents.renderResultCard(recs[i], i + 1, staggerIndex);
      }
      gridHtml += '</div>';
      resultsArea.insertAdjacentHTML('beforeend', gridHtml);
    }
  }

  // --- No Results Rendering ---
  function renderNoResultsState(message) {
    resultsArea.innerHTML = `
      <div class="empty-container glass-panel animate-fade-in-up">
        <div class="empty-icon-group">
          <span class="material-symbols-outlined">sentiment_dissatisfied</span>
          <span class="material-symbols-outlined">restaurant</span>
        </div>
        <h3 class="empty-title">No Recommendations Found</h3>
        <p class="empty-message">${message}</p>
        <button class="btn-primary mt-4" id="empty-reset-btn">
          <span class="material-symbols-outlined">refresh</span> Modify Filters
        </button>
      </div>
    `;
    metadataContainer.innerHTML = '';
    
    document.getElementById('empty-reset-btn').addEventListener('click', () => {
      window.scrollTo({ top: document.querySelector('form').offsetTop - 120, behavior: 'smooth' });
    });
  }

  // --- Error Panel Rendering ---
  function renderErrorBox(message) {
    resultsArea.innerHTML = window.FoodieComponents.renderErrorState(
      "Service Offline",
      message,
      true
    );
    metadataContainer.innerHTML = '';
    
    const retryBtn = document.getElementById('error-retry-btn');
    if (retryBtn) {
      retryBtn.addEventListener('click', () => {
        submitBtn.click(); // Re-trigger search submit event
      });
    }
  }

  // --- Reset/New Search Actions ---
  const handleReset = () => {
    // Scroll back to search form smoothly
    window.scrollTo({ top: document.querySelector('form').offsetTop - 120, behavior: 'smooth' });
    
    // Wait briefly for scroll to start, then animate out results
    setTimeout(() => {
      resultsContainer.classList.add('hidden');
      resultsArea.innerHTML = '';
      metadataContainer.innerHTML = '';
    }, 300);
  };
  
  if (newSearchBtn) newSearchBtn.addEventListener('click', handleReset);
  if (clearSearchBtnHeader) clearSearchBtnHeader.addEventListener('click', handleReset);
});
