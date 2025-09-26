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

// Base metal genres with their common variations and subgenres
const GENRE_HIERARCHY = {
  'Black Metal': {
    keywords: ['black', 'blackened', 'blackgaze', 'atmospheric black', 'symphonic black', 'melodic black', 'raw black', 'depressive black'],
    priority: 10,
    color: '#1a1a1a'
  },
  'Death Metal': {
    keywords: ['death', 'brutal death', 'technical death', 'melodic death', 'progressive death', 'old school death', 'blackened death'],
    priority: 9,
    color: '#8B0000'
  },
  'Thrash Metal': {
    keywords: ['thrash', 'crossover thrash', 'blackened thrash', 'technical thrash', 'groove thrash'],
    priority: 8,
    color: '#FF4500'
  },
  'Heavy Metal': {
    keywords: ['heavy', 'traditional heavy', 'classic heavy', 'nwobhm', 'speed metal'],
    priority: 7,
    color: '#4169E1'
  },
  'Doom Metal': {
    keywords: ['doom', 'sludge', 'stoner', 'funeral doom', 'epic doom', 'traditional doom', 'atmospheric doom'],
    priority: 6,
    color: '#2F4F4F'
  },
  'Power Metal': {
    keywords: ['power', 'symphonic power', 'melodic power', 'epic power', 'progressive power'],
    priority: 5,
    color: '#FFD700'
  },
  'Progressive Metal': {
    keywords: ['progressive', 'prog', 'technical', 'djent', 'post-metal', 'experimental'],
    priority: 4,
    color: '#9370DB'
  },
  'Folk Metal': {
    keywords: ['folk', 'pagan', 'viking', 'celtic', 'medieval', 'acoustic'],
    priority: 3,
    color: '#228B22'
  },
  'Symphonic Metal': {
    keywords: ['symphonic', 'orchestral', 'operatic', 'gothic symphonic'],
    priority: 2,
    color: '#DC143C'
  },
  'Gothic Metal': {
    keywords: ['gothic', 'darkwave', 'dark metal', 'atmospheric gothic'],
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
 * Check if a genre matches a main category
 */
function matchesCategory(genre: string, category: string, keywords: string[]): boolean {
  const normalizedGenre = normalizeGenre(genre);
  const normalizedCategory = normalizeGenre(category);
  
  // Direct match
  if (normalizedGenre.includes(normalizedCategory)) {
    return true;
  }
  
  // Keyword match
  return keywords.some(keyword => 
    normalizedGenre.includes(normalizeGenre(keyword))
  );
}

/**
 * Extract modifiers from genre string
 */
function extractModifiers(genre: string): string[] {
  const normalizedGenre = normalizeGenre(genre);
  return COMMON_MODIFIERS.filter(modifier => 
    normalizedGenre.includes(modifier)
  );
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
  
  // Categorize each genre
  genreMap.forEach((count, genre) => {
    let categorized = false;
    
    // Try to match with main categories
    for (const [categoryName, config] of Object.entries(GENRE_HIERARCHY)) {
      if (matchesCategory(genre, categoryName, config.keywords)) {
        const group = mainGenres.find(g => g.name === categoryName);
        if (group) {
          group.count += count;
          group.subgenres.push(genre);
          categorized = true;
          break;
        }
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
 * Check if an album matches selected genre groups
 */
export function albumMatchesGenreGroups(
  albumGenre: string, 
  selectedGroups: string[]
): boolean {
  if (selectedGroups.length === 0) return true;
  
  const albumGenres = albumGenre.split(/[\/,;]/).map(g => g.trim());
  
  return selectedGroups.some(groupName => {
    // Check if it's a main category
    const categoryConfig = GENRE_HIERARCHY[groupName as keyof typeof GENRE_HIERARCHY];
    if (categoryConfig) {
      return albumGenres.some(genre => 
        matchesCategory(genre, groupName, categoryConfig.keywords)
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
