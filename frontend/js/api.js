/* ═══════════════════════════════════════════════════════════════════════
   FoodieAI — API Client Module (api.js)
   ═══════════════════════════════════════════════════════════════════════ */

// Base URL detection. Prefers same origin when served by FastAPI, fallbacks to localhost:8000
const BASE_URL = window.location.origin.includes('localhost') 
  ? window.location.origin 
  : 'http://localhost:8000';

// Simple in-memory caches
let cachedLocations = null;
let cachedCuisines = null;

/**
 * Helper to execute a fetch request with a configurable timeout
 */
async function fetchWithTimeout(resource, options = {}) {
  const { timeout = 30000 } = options;
  
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), timeout);
  
  const response = await fetch(resource, {
    ...options,
    signal: controller.signal
  });
  clearTimeout(id);
  return response;
}

/**
 * Custom API Error representation
 */
class ApiError extends Error {
  constructor(message, status, data = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.data = data;
  }
}

/**
 * GET /health — Checks if the API backend is healthy and dataset loaded
 */
async function checkHealth() {
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/health`);
    if (!response.ok) {
      throw new ApiError(`Health check failed with status ${response.status}`, response.status);
    }
    return await response.json();
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Connection timed out while checking server health.');
    }
    throw error;
  }
}

/**
 * GET /locations — Fetches list of valid locations
 */
async function fetchLocations() {
  if (cachedLocations) {
    return cachedLocations;
  }
  
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/locations`);
    if (!response.ok) {
      throw new ApiError(`Failed to fetch locations: ${response.statusText}`, response.status);
    }
    const data = await response.json();
    cachedLocations = data.locations || [];
    return cachedLocations;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Timeout while retrieving locations.');
    }
    throw error;
  }
}

/**
 * GET /cuisines — Fetches list of known cuisines
 */
async function fetchCuisines() {
  if (cachedCuisines) {
    return cachedCuisines;
  }
  
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/cuisines`);
    if (!response.ok) {
      throw new ApiError(`Failed to fetch cuisines: ${response.statusText}`, response.status);
    }
    const data = await response.json();
    cachedCuisines = data.cuisines || [];
    return cachedCuisines;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('Timeout while retrieving cuisines.');
    }
    throw error;
  }
}

/**
 * POST /recommend — Posts recommendation criteria to get ranked AI recommendations
 */
async function fetchRecommendations(preferences) {
  try {
    const response = await fetchWithTimeout(`${BASE_URL}/recommend`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify(preferences)
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      // Return details for validation error (422) or generic errors
      throw new ApiError(
        data.detail?.message || data.detail || 'Failed to fetch recommendations', 
        response.status, 
        data.detail
      );
    }
    
    return data;
  } catch (error) {
    if (error.name === 'AbortError') {
      throw new Error('AI recommendation engine took too long to respond. Please try again.');
    }
    throw error;
  }
}

// Export functions to global scope for other modules
window.FoodieApi = {
  checkHealth,
  fetchLocations,
  fetchCuisines,
  fetchRecommendations
};
