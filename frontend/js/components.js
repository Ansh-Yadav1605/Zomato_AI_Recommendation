/* ═══════════════════════════════════════════════════════════════════════
   FoodieAI — UI Rendering Components (components.js)
   ═══════════════════════════════════════════════════════════════════════ */

/**
 * Maps a cuisine list to a descriptive Google Material Icon
 */
function getCuisineIcon(cuisineStr = '') {
  const c = cuisineStr.toLowerCase();
  if (c.includes('pizza') || c.includes('italian')) return 'local_pizza';
  if (c.includes('burger') || c.includes('fast food')) return 'fastfood';
  if (c.includes('sushi') || c.includes('asian') || c.includes('japanese') || c.includes('chinese')) return 'ramen_dining';
  if (c.includes('bakery') || c.includes('dessert') || c.includes('cake') || c.includes('sweet')) return 'cake';
  if (c.includes('cafe') || c.includes('coffee') || c.includes('tea')) return 'local_cafe';
  if (c.includes('beer') || c.includes('bar') || c.includes('pub') || c.includes('wine')) return 'sports_bar';
  if (c.includes('healthy') || c.includes('salad') || c.includes('vegan') || c.includes('vegetarian')) return 'nutrition';
  if (c.includes('north indian') || c.includes('biryani') || c.includes('south indian') || c.includes('indian')) return 'dinner_dining';
  return 'restaurant'; // default
}

/**
 * Generates alternating high-end radial/linear gradients for image-less cards
 */
function getGradientBackground(index) {
  const gradients = [
    'linear-gradient(135deg, rgba(255, 107, 53, 0.25) 0%, rgba(247, 201, 72, 0.08) 50%, rgba(18, 18, 29, 0.95) 100%)', // Coral-Amber
    'linear-gradient(135deg, rgba(65, 238, 194, 0.25) 0%, rgba(0, 210, 167, 0.08) 50%, rgba(18, 18, 29, 0.95) 100%)',   // Teal-Cyan
    'linear-gradient(135deg, rgba(239, 193, 65, 0.25) 0%, rgba(209, 166, 38, 0.08) 50%, rgba(18, 18, 29, 0.95) 100%)',   // Amber-Gold
    'linear-gradient(135deg, rgba(255, 181, 157, 0.2) 0%, rgba(89, 65, 57, 0.08) 50%, rgba(18, 18, 29, 0.95) 100%)',     // Muted Rose
    'linear-gradient(135deg, rgba(85, 252, 208, 0.2) 0%, rgba(0, 81, 63, 0.08) 50%, rgba(18, 18, 29, 0.95) 100%)'       // Muted Mint
  ];
  return gradients[index % gradients.length];
}

/**
 * Renders HTML for stars (filled / empty)
 */
function renderStarRating(rating) {
  const rounded = Math.round(rating);
  let starsHtml = '<div class="star-rating">';
  for (let i = 1; i <= 5; i++) {
    if (i <= rounded) {
      starsHtml += '<span class="material-symbols-outlined">star</span>';
    } else {
      starsHtml += '<span class="material-symbols-outlined empty">star</span>';
    }
  }
  starsHtml += '</div>';
  return starsHtml;
}

/**
 * Renders individual cuisine pills
 */
function renderCuisineTags(cuisineStr = '') {
  return cuisineStr
    .split(',')
    .map(c => c.trim())
    .filter(c => c.length > 0)
    .map(c => `<span class="tag">${c}</span>`)
    .join('');
}

/**
 * Renders the top-ranked featured recommendation card
 */
function renderFeaturedCard(restaurant, rank) {
  const icon = getCuisineIcon(restaurant.cuisine);
  const gradient = getGradientBackground(rank - 1);
  const starDisplay = renderStarRating(restaurant.rating);
  const cuisineTags = renderCuisineTags(restaurant.cuisine);

  return `
    <div class="glass-panel featured-card hover-glow-card animate-fade-in-up stagger-3 group">
      <div class="card-image flex items-center justify-center" style="background: ${gradient};">
        <!-- Floating Brand Backdrop Design instead of a food image -->
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none opacity-30 select-none">
          <span class="material-symbols-outlined text-[120px] text-primary animate-float" style="font-variation-settings: 'FILL' 0;">${icon}</span>
        </div>
        <div class="card-image-overlay"></div>
        <div class="card-badge">
          <span class="badge badge-top">
            <span class="material-symbols-outlined">stars</span> AI Top Match
          </span>
          <span class="badge badge-rank">#${rank}</span>
        </div>
        
        <!-- Large centered decorative icon -->
        <div class="relative z-10 flex flex-col items-center gap-2 group-hover:scale-110 transition-transform duration-500">
          <div class="w-20 h-20 rounded-full bg-white/5 border border-white/10 flex items-center justify-center shadow-lg backdrop-blur-md">
            <span class="material-symbols-outlined text-primary text-[42px]">${icon}</span>
          </div>
          <span class="text-xs uppercase tracking-widest text-on-surface-variant font-semibold">Gourmet Curation</span>
        </div>
      </div>
      
      <div class="card-body">
        <div class="card-title-row">
          <div>
            <h3 class="card-title">${restaurant.restaurant_name}</h3>
            <div class="card-tags mt-2">${cuisineTags}</div>
          </div>
          <div class="card-rating">
            <div class="rating-badge">
              <span class="rating-num">${Number(restaurant.rating).toFixed(1)}</span>
              <span class="material-symbols-outlined" style="font-variation-settings: 'FILL' 1;">star</span>
            </div>
            <span class="cost-label">Est. ${restaurant.estimated_cost}</span>
          </div>
        </div>
        
        <div class="ai-insight">
          <span class="material-symbols-outlined ai-insight-icon">auto_awesome</span>
          <h4 class="ai-insight-title">AI Insight</h4>
          <p class="ai-insight-text">"${restaurant.explanation}"</p>
        </div>
        
        <div class="card-actions">
          <button class="btn-secondary" onclick="alert('Added to your favorite list!')">
            <span class="material-symbols-outlined">bookmark_add</span> Save Place
          </button>
          <button class="btn-action" onclick="alert('Booking functionality would be linked here!')">
            Book Table <span class="material-symbols-outlined">arrow_forward</span>
          </button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Renders standard secondary recommendation cards
 */
function renderResultCard(restaurant, rank, staggerIndex) {
  const icon = getCuisineIcon(restaurant.cuisine);
  const gradient = getGradientBackground(rank - 1);
  const starDisplay = renderStarRating(restaurant.rating);
  const cuisineTags = renderCuisineTags(restaurant.cuisine);

  return `
    <div class="glass-panel result-card hover-glow-card animate-fade-in-up stagger-${staggerIndex} group">
      <div class="card-image flex items-center justify-center" style="background: ${gradient}; height: 160px;">
        <div class="absolute inset-0 flex items-center justify-center pointer-events-none opacity-20 select-none">
          <span class="material-symbols-outlined text-[90px] text-primary" style="font-variation-settings: 'FILL' 0;">${icon}</span>
        </div>
        <div class="card-image-overlay" style="background: linear-gradient(to top, var(--surface-dim) 0%, transparent 80%);"></div>
        <div class="card-badge">
          <span class="badge badge-rank">#${rank}</span>
        </div>
        
        <div class="relative z-10 flex flex-col items-center gap-1 group-hover:scale-105 transition-transform duration-500">
          <div class="w-14 h-14 rounded-full bg-white/5 border border-white/10 flex items-center justify-center shadow-md backdrop-blur-md">
            <span class="material-symbols-outlined text-primary text-[28px]">${icon}</span>
          </div>
        </div>
      </div>
      
      <div class="card-body" style="padding: var(--space-5);">
        <div class="card-title-row" style="margin-bottom: var(--space-3);">
          <div>
            <h3 class="card-title" style="font-size: 20px;">${restaurant.restaurant_name}</h3>
            <div class="card-tags mt-1">${cuisineTags}</div>
          </div>
          <div class="card-rating">
            <div class="rating-badge" style="padding: 2px 8px;">
              <span class="rating-num" style="font-size: 13px;">${Number(restaurant.rating).toFixed(1)}</span>
              <span class="material-symbols-outlined" style="font-size: 12px; font-variation-settings: 'FILL' 1;">star</span>
            </div>
            <span class="cost-label" style="font-size: 9px;">${restaurant.estimated_cost}</span>
          </div>
        </div>
        
        <p class="card-desc text-sm text-on-surface-variant italic mb-4" style="line-clamp: 3; -webkit-line-clamp: 3; display: -webkit-box; -webkit-box-orient: vertical; overflow: hidden;">
          "${restaurant.explanation}"
        </p>
        
        <div class="card-actions" style="margin-top: auto; padding-top: var(--space-2); justify-content: space-between;">
          <button class="btn-secondary" style="font-size: 12px; padding: 6px 12px;" onclick="alert('Saved to favorites!')">
            <span class="material-symbols-outlined" style="font-size: 16px;">bookmark</span> Save
          </button>
          <button class="btn-action" style="font-size: 12px; padding: 6px 12px;" onclick="alert('Booking popup triggers here!')">
            Book <span class="material-symbols-outlined" style="font-size: 16px;">chevron_right</span>
          </button>
        </div>
      </div>
    </div>
  `;
}

/**
 * Render the stats bar containing meta details
 */
function renderMetadataBar(metadata, responseTimeMs, modelName) {
  const filtersHtml = [
    metadata.matched_location ? `📍 ${metadata.matched_location}` : null,
    metadata.matched_cuisine ? `🍳 ${metadata.matched_cuisine}` : null,
    metadata.constraints_relaxed && metadata.constraints_relaxed.length > 0 
      ? `⚠️ Relaxed: ${metadata.constraints_relaxed.join(', ')}` 
      : null
  ].filter(Boolean).map(f => `<span class="badge" style="background: rgba(255,255,255,0.05); border: 1px solid rgba(255,255,255,0.1); color: var(--on-surface-variant);">${f}</span>`).join(' ');

  return `
    <div class="metadata-stats">
      <div class="metadata-stat">
        <span class="material-symbols-outlined text-secondary">analytics</span>
        <span class="stat-value">${metadata.candidates_found || 0}</span> candidates analyzed
      </div>
      <div class="metadata-divider"></div>
      <div class="metadata-stat">
        <span class="material-symbols-outlined text-primary">filter_list</span>
        <div style="display: flex; gap: 6px;">
          ${filtersHtml || '<span class="text-caption">Default filters</span>'}
        </div>
      </div>
      <div class="metadata-divider"></div>
      <div class="metadata-stat">
        <span class="material-symbols-outlined text-tertiary font-medium">smart_toy</span>
        <span class="stat-value">${modelName || 'Llama 3'}</span>
      </div>
      <div class="metadata-divider"></div>
      <div class="metadata-stat">
        <span class="material-symbols-outlined text-secondary-fixed">bolt</span>
        <span class="stat-value">${(responseTimeMs / 1000).toFixed(1)}s</span> response
      </div>
    </div>
  `;
}

/**
 * Renders skeleton card placeholders during API loads
 */
function renderSkeletonCards(count = 3) {
  let skeletonsHtml = '<div class="results-grid">';
  for (let i = 0; i < count; i++) {
    skeletonsHtml += `
      <div class="skeleton-card shimmer-bg">
        <div class="skeleton-image"></div>
        <div class="skeleton-body">
          <div class="skeleton-line h-lg w-75"></div>
          <div class="skeleton-line w-50"></div>
          <div class="skeleton-line w-100" style="margin-top: 10px;"></div>
          <div class="skeleton-line w-100"></div>
        </div>
      </div>
    `;
  }
  skeletonsHtml += '</div>';
  return skeletonsHtml;
}

/**
 * Renders the error state box with clean illustrations
 */
function renderErrorState(title, message, isRetryable = true) {
  return `
    <div class="error-container glass-panel animate-fade-in-up">
      <span class="material-symbols-outlined error-icon">warning</span>
      <h3 class="error-title">${title}</h3>
      <p class="error-message">${message}</p>
      ${isRetryable ? `
        <button class="btn-primary mt-4 animate-pulse-glow" id="error-retry-btn">
          <span class="material-symbols-outlined">refresh</span> Try Again
        </button>
      ` : ''}
    </div>
  `;
}

// Export functions to global scope
window.FoodieComponents = {
  renderFeaturedCard,
  renderResultCard,
  renderMetadataBar,
  renderSkeletonCards,
  renderErrorState
};
