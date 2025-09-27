/**
 * Smart Genre Grouping Utility
 * Groups and categorizes metal genres into hierarchical structures
 */

export interface GenreGroup {
  name: string;
  count: number;
  color: string;
  subgenres: string[];
  priority: number; // Higher priority = shown first
}

export interface GenreHierarchy {
  mainGenres: GenreGroup[];
  modifiers: string[];
  totalGenres: number;
  totalAlbums: number;
}

// Base metal genres with their core identifiers and variations
const GENRE_HIERARCHY = {
  'Death Metal': {
    coreWords: ['death'],
    variations: ['brutal death', 'technical death', 'melodic death', 'progressive death', 'old school death', 'blackened death'],
    priority: 10,
    color: '#8B0000'
  },
  'Black Metal': {
    coreWords: ['black'],
    variations: ['atmospheric black', 'symphonic black', 'melodic black', 'raw black', 'depressive black', 'post-black', 'pagan black'],
    priority: 9,
    color: '#1a1a1a'
  },
  'Thrash Metal': {
    coreWords: ['thrash'],
    variations: ['crossover thrash', 'blackened thrash', 'technical thrash', 'groove thrash', 'speed thrash'],
    priority: 8,
    color: '#FF4500'
  },
  'Progressive Metal': {
    coreWords: ['progressive', 'prog'],
    variations: ['djent', 'post-metal', 'experimental metal', 'technical progressive', 'progressive metal'],
    priority: 7,
    color: '#9370DB'
  },
  'Doom Metal': {
    coreWords: ['doom'],
    variations: ['sludge', 'stoner', 'funeral doom', 'epic doom', 'traditional doom', 'atmospheric doom', 'drone'],
    priority: 6,
    color: '#2F4F4F'
  },
  'Heavy Metal': {
    coreWords: ['heavy'],
    variations: ['traditional heavy', 'classic heavy', 'nwobhm', 'speed metal', 'classic metal'],
    priority: 5,
    color: '#4169E1'
  },
  'Power Metal': {
    coreWords: ['power'],
    variations: ['symphonic power', 'melodic power', 'epic power', 'progressive power', 'speed power'],
    priority: 4,
    color: '#FFD700'
  },
  'Folk Metal': {
    coreWords: ['folk', 'pagan', 'viking'],
    variations: ['celtic metal', 'medieval metal', 'acoustic folk'],
    priority: 3,
    color: '#228B22'
  },
  'Symphonic Metal': {
    coreWords: ['symphonic', 'orchestral'],
    variations: ['operatic metal', 'cinematic metal'],
    priority: 2,
    color: '#DC143C'
  },
  'Gothic Metal': {
    coreWords: ['gothic'],
    variations: ['darkwave metal', 'dark metal', 'atmospheric gothic'],
    priority: 1,
    color: '#800080'
  }
};

// Common modifiers that should be grouped separately
const COMMON_MODIFIERS = [
  'melodic', 'atmospheric', 'symphonic', 'technical', 'brutal', 'progressive',
  'experimental', 'ambient', 'industrial', 'electronic', 'acoustic', 'instrumental'
];

/**
 * Normalize genre string for comparison
 */
function normalizeGenre(genre: string): string {
  return genre.toLowerCase()
    .replace(/[^\w\s]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

/**
 * Extract the primary metal genre from a complex genre string
 * Uses hierarchical priority to determine the main classification
 */
export function extractPrimaryGenre(genre: string): string | null {
  if (!genre) return null;
  
  const normalizedGenre = normalizeGenre(genre);
  const words = normalizedGenre.split(/\s+/);
  
  // Check for exact core word matches with word boundaries
  for (const [categoryName, config] of Object.entries(GENRE_HIERARCHY)) {
    // Check core words with word boundaries
    for (const coreWord of config.coreWords) {
      const regex = new RegExp(`\\b${normalizeGenre(coreWord)}\\b`);
      if (regex.test(normalizedGenre)) {
        // Make sure it's actually metal (contains 'metal' or is a known metal term)
        if (normalizedGenre.includes('metal') || 
            ['death', 'black', 'thrash', 'doom', 'power', 'folk', 'gothic', 'symphonic'].includes(coreWord)) {
          return categoryName;
        }
      }
    }
    
    // Check variations for exact matches
    for (const variation of config.variations) {
      if (normalizedGenre === normalizeGenre(variation)) {
        return categoryName;
      }
    }
  }
  
  // Handle single word cases (e.g., "Death" -> "Death Metal")
  for (const [categoryName, config] of Object.entries(GENRE_HIERARCHY)) {
    for (const coreWord of config.coreWords) {
      if (normalizedGenre === normalizeGenre(coreWord)) {
        return categoryName;
      }
    }
  }
  
  return null;
}

/**
 * Extract modifiers from a genre string (excluding the primary genre)
 */
export function extractModifiers(genre: string): string[] {
  if (!genre) return [];
  
  const normalizedGenre = normalizeGenre(genre);
  const primaryGenre = extractPrimaryGenre(genre);
  
  if (!primaryGenre) return [];
  
  const config = GENRE_HIERARCHY[primaryGenre as keyof typeof GENRE_HIERARCHY];
  if (!config) return [];
  
  // Remove primary genre words from the string
  let modifiedGenre = normalizedGenre;
  for (const coreWord of config.coreWords) {
    const regex = new RegExp(`\\b${normalizeGenre(coreWord)}\\b`, 'g');
    modifiedGenre = modifiedGenre.replace(regex, '');
  }
  modifiedGenre = modifiedGenre.replace(/\bmetal\b/g, '').trim();
  
  // Extract remaining meaningful words as modifiers
  const words = modifiedGenre.split(/\s+/).filter(word => word.length > 2);
  const modifiers = words.filter(word => 
    COMMON_MODIFIERS.includes(word) || 
    /^(atmospheric|symphonic|technical|brutal|melodic|progressive|experimental|ambient|industrial|electronic|acoustic|instrumental)$/.test(word)
  ).map(word => {
    // Capitalize first letter for consistency
    return word.charAt(0).toUpperCase() + word.slice(1);
  });
  
  return Array.from(new Set(modifiers)); // Remove duplicates
}

/**
 * Improved category matching using hierarchical priority
 */
export function matchesCategoryImproved(genre: string, category: string): boolean {
  if (!genre || !category) return false;
  
  const primaryGenre = extractPrimaryGenre(genre);
  return primaryGenre === category;
}

/**
 * Legacy function for backward compatibility (deprecated)
 * @deprecated Use matchesCategoryImproved instead
 */
function matchesCategory(genre: string, category: string, keywords: string[]): boolean {
  return matchesCategoryImproved(genre, category);
}


/**
 * Group genres into hierarchical structure
 */
export function groupGenres(genreMap: Map<string, number>): GenreHierarchy {
  const mainGenres: GenreGroup[] = [];
  const modifiers = new Set<string>();
  const uncategorized: { genre: string; count: number }[] = [];
  
  // Initialize main genre groups
  Object.entries(GENRE_HIERARCHY).forEach(([categoryName, config]) => {
    mainGenres.push({
      name: categoryName,
      count: 0,
      color: config.color,
      subgenres: [],
      priority: config.priority
    });
  });
  
  // Categorize each genre using improved hierarchical matching
  genreMap.forEach((count, genre) => {
    let categorized = false;
    
    // Use improved primary genre detection
    const primaryGenre = extractPrimaryGenre(genre);
    if (primaryGenre) {
      const group = mainGenres.find(g => g.name === primaryGenre);
      if (group) {
        group.count += count;
        group.subgenres.push(genre);
        categorized = true;
      }
    }
    
    // Extract modifiers
    const genreModifiers = extractModifiers(genre);
    genreModifiers.forEach(modifier => modifiers.add(modifier));
    
    // If not categorized, add to uncategorized
    if (!categorized) {
      uncategorized.push({ genre, count });
    }
  });
  
  // Add significant uncategorized genres as their own groups
  uncategorized
    .filter(item => item.count >= 3) // Only include genres with 3+ albums
    .sort((a, b) => b.count - a.count)
    .slice(0, 5) // Limit to top 5 uncategorized
    .forEach(item => {
      mainGenres.push({
        name: item.genre,
        count: item.count,
        color: generateGenreColor(item.genre),
        subgenres: [item.genre],
        priority: 0
      });
    });
  
  // Remove empty groups and sort by priority and count
  const filteredMainGenres = mainGenres
    .filter(group => group.count > 0)
    .sort((a, b) => {
      if (a.priority !== b.priority) {
        return b.priority - a.priority;
      }
      return b.count - a.count;
    });
  
  const totalGenres = genreMap.size;
  const totalAlbums = Array.from(genreMap.values()).reduce((sum, count) => sum + count, 0);
  
  return {
    mainGenres: filteredMainGenres,
    modifiers: Array.from(modifiers).sort(),
    totalGenres,
    totalAlbums
  };
}

/**
 * Generate color for genre (fallback for uncategorized genres)
 */
function generateGenreColor(genre: string): string {
  const colors = [
    '#f44336', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5', 
    '#2196f3', '#00bcd4', '#009688', '#4caf50', '#ff9800',
    '#ff5722', '#795548', '#607d8b', '#e65100', '#bf360c'
  ];
  let hash = 0;
  for (let i = 0; i < genre.length; i++) {
    hash = genre.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

/**
 * Check if an album matches selected genre groups using improved matching
 */
export function albumMatchesGenreGroups(
  albumGenre: string, 
  selectedGroups: string[]
): boolean {
  if (selectedGroups.length === 0) return true;
  
  const albumGenres = albumGenre.split(/[\/,;]/).map(g => g.trim());
  
  return selectedGroups.some(groupName => {
    // Check if it's a main category using improved matching
    const categoryConfig = GENRE_HIERARCHY[groupName as keyof typeof GENRE_HIERARCHY];
    if (categoryConfig) {
      return albumGenres.some(genre => 
        matchesCategoryImproved(genre, groupName)
      );
    }
    
    // Direct match for uncategorized genres
    return albumGenres.some(genre => 
      normalizeGenre(genre) === normalizeGenre(groupName)
    );
  });
}

/**
 * Get smart genre suggestions based on current selection
 */
export function getGenreSuggestions(
  selectedGroups: string[],
  allGroups: GenreGroup[]
): GenreGroup[] {
  if (selectedGroups.length === 0) {
    return allGroups.slice(0, 8); // Show top 8 when nothing selected
  }
  
  // Show related genres based on current selection
  const suggestions = allGroups
    .filter(group => !selectedGroups.includes(group.name))
    .sort((a, b) => b.count - a.count)
    .slice(0, 5);
  
  return suggestions;
}
