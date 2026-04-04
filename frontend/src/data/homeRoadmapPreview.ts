export type HomeRoadmapOutcome = {
  id: string
  title: string
  status: 'completed' | 'current' | 'upcoming'
  subtext?: string
}

export type HomeRoadmapPreview = {
  cardTitle: string
  cardSubtitle: string
  outcomes: HomeRoadmapOutcome[]
  startHerePath: string
  fullRoadmapPath: string
}

export const HOME_ROADMAP_PREVIEW: Record<string, HomeRoadmapPreview> = {
  '/roadmap': {
    cardTitle: 'Financial Accounting Roadmap',
    cardSubtitle: '6 learning outcomes · Personalized for you',
    outcomes: [
      { id: '1', title: 'Reading a Financial Statement', status: 'completed' },
      {
        id: '2',
        title: 'The Income Statement',
        status: 'current',
        subtext: 'Based on your background, this is the right place to start.',
      },
      { id: '3', title: 'The Balance Sheet', status: 'upcoming' },
      { id: '4', title: 'Cash Flow Basics', status: 'upcoming' },
      { id: '5', title: 'Ratio Analysis', status: 'upcoming' },
      { id: '6', title: 'Interpreting Performance', status: 'upcoming' },
    ],
    startHerePath: '/module/income-statement',
    fullRoadmapPath: '/roadmap',
  },
  '/roadmap/cs101': {
    cardTitle: 'Intro to Python Roadmap',
    cardSubtitle: '6 learning outcomes · Personalized for you',
    outcomes: [
      { id: '1', title: 'Python Basics & Syntax', status: 'completed' },
      {
        id: '2',
        title: 'Variables and Data Types',
        status: 'current',
        subtext: 'Learn about integers, strings, booleans, and type conversion.',
      },
      { id: '3', title: 'Control Flow', status: 'upcoming' },
      { id: '4', title: 'Functions and Modules', status: 'upcoming' },
      { id: '5', title: 'Data Structures', status: 'upcoming' },
      { id: '6', title: 'File I/O and Error Handling', status: 'upcoming' },
    ],
    startHerePath: '/module/cs101-variables',
    fullRoadmapPath: '/roadmap/cs101',
  },
  '/roadmap/mktg440': {
    cardTitle: 'Digital Marketing Roadmap',
    cardSubtitle: '6 learning outcomes · Personalized for you',
    outcomes: [
      { id: '1', title: 'Digital Marketing Fundamentals', status: 'completed' },
      {
        id: '2',
        title: 'SEO Basics',
        status: 'current',
        subtext: 'Master search engine optimization and content discovery.',
      },
      { id: '3', title: 'Social Media Strategy', status: 'upcoming' },
      { id: '4', title: 'Email Marketing', status: 'upcoming' },
      { id: '5', title: 'Analytics and Metrics', status: 'upcoming' },
      { id: '6', title: 'Campaign Optimization', status: 'upcoming' },
    ],
    startHerePath: '/module/mktg440-seo',
    fullRoadmapPath: '/roadmap/mktg440',
  },
  '/roadmap/hist102': {
    cardTitle: 'World History II Roadmap',
    cardSubtitle: '6 learning outcomes · Personalized for you',
    outcomes: [
      { id: '1', title: 'Age of Revolutions', status: 'completed' },
      {
        id: '2',
        title: 'Industrial Revolution',
        status: 'current',
        subtext: 'Explore the transformation of society through industrialization.',
      },
      { id: '3', title: 'World War I', status: 'upcoming' },
      { id: '4', title: 'World War II', status: 'upcoming' },
      { id: '5', title: 'Cold War Era', status: 'upcoming' },
      { id: '6', title: 'Modern Globalization', status: 'upcoming' },
    ],
    startHerePath: '/module/hist102-industrial',
    fullRoadmapPath: '/roadmap/hist102',
  },
  '/roadmap/econ201': {
    cardTitle: 'Macroeconomics Roadmap',
    cardSubtitle: '6 learning outcomes · Personalized for you',
    outcomes: [
      { id: '1', title: 'Economic Foundations', status: 'completed' },
      {
        id: '2',
        title: 'GDP and National Income',
        status: 'current',
        subtext: 'Understanding how we measure economic output and growth.',
      },
      { id: '3', title: 'Inflation and Price Indices', status: 'upcoming' },
      { id: '4', title: 'Unemployment and Labor Markets', status: 'upcoming' },
      { id: '5', title: 'Monetary Policy', status: 'upcoming' },
      { id: '6', title: 'Fiscal Policy', status: 'upcoming' },
    ],
    startHerePath: '/module/econ201-gdp',
    fullRoadmapPath: '/roadmap/econ201',
  },
  '/roadmap/python': {
    cardTitle: 'Intro to Computer Science & Python',
    cardSubtitle: '9 learning outcomes · Tailored for Alice',
    outcomes: [
      { id: '1', title: 'Introduction to Computation', status: 'completed' },
      {
        id: '2',
        title: 'Branching and Iteration',
        status: 'current',
        subtext: 'Learn control flow with if statements and loops - includes video lectures.',
      },
      { id: '3', title: 'String Manipulation', status: 'upcoming' },
      { id: '4', title: 'Functions and Decomposition', status: 'upcoming' },
      { id: '5', title: 'Tuples, Lists, and Dictionaries', status: 'upcoming' },
      { id: '6', title: 'Recursion and Testing', status: 'upcoming' },
      { id: '7', title: 'Object-Oriented Programming', status: 'upcoming' },
      { id: '8', title: 'Algorithm Complexity', status: 'upcoming' },
      { id: '9', title: 'Final Project', status: 'upcoming' },
    ],
    startHerePath: '/module/python-branching',
    fullRoadmapPath: '/roadmap/python',
  },
  '/roadmap/financing': {
    cardTitle: 'Financing Economic Development',
    cardSubtitle: '8 learning outcomes · Tailored for Bob',
    outcomes: [
      { id: '1', title: 'Capital Markets Fundamentals', status: 'completed' },
      {
        id: '2',
        title: 'Financial Analysis Methods',
        status: 'current',
        subtext: 'Master business and real estate financial statements - rich with case examples.',
      },
      { id: '3', title: 'Business Finance Tools', status: 'upcoming' },
      { id: '4', title: 'Real Estate Project Financing', status: 'upcoming' },
      { id: '5', title: 'Federal Development Programs', status: 'upcoming' },
      { id: '6', title: 'Public Finance Instruments', status: 'upcoming' },
      { id: '7', title: 'Sustainable Development Finance', status: 'upcoming' },
      { id: '8', title: 'Development Finance Management', status: 'upcoming' },
    ],
    startHerePath: '/module/financing-analysis',
    fullRoadmapPath: '/roadmap/financing',
  },
  '/roadmap/accounting': {
    cardTitle: 'Financial & Managerial Accounting',
    cardSubtitle: '10 learning outcomes · Tailored for Charles',
    outcomes: [
      { id: '1', title: 'Accounting Fundamentals', status: 'completed' },
      { id: '2', title: 'Double-Entry Bookkeeping', status: 'completed' },
      {
        id: '3',
        title: 'Financial Statement Preparation',
        status: 'current',
        subtext: 'Practice with interactive exercises and flashcard reviews.',
      },
      { id: '4', title: 'Revenue Recognition', status: 'upcoming' },
      { id: '5', title: 'Inventory Valuation', status: 'upcoming' },
      { id: '6', title: 'Long-Lived Assets', status: 'upcoming' },
      { id: '7', title: 'Cost Accounting Basics', status: 'upcoming' },
      { id: '8', title: 'Budgeting and Variance Analysis', status: 'upcoming' },
      { id: '9', title: 'Performance Measurement', status: 'upcoming' },
      { id: '10', title: 'Decision Making with Accounting Data', status: 'upcoming' },
    ],
    startHerePath: '/module/accounting-statements',
    fullRoadmapPath: '/roadmap/accounting',
  },
}
