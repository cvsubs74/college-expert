import { BrowserRouter as Router, Routes, Route, Link, useLocation, Outlet } from 'react-router-dom';
import { AcademicCapIcon, DocumentTextIcon, ChartBarIcon, ChatBubbleLeftRightIcon, ArrowRightOnRectangleIcon, BookOpenIcon, BuildingLibraryIcon, SparklesIcon, RocketLaunchIcon } from '@heroicons/react/24/outline';
import Profile from './pages/Profile';
import Chat from './pages/Chat';
import KnowledgeBase from './pages/KnowledgeBase';
import UniversityExplorer from './pages/UniversityExplorer';
import MyLaunchpad from './pages/MyLaunchpad';
import LandingPage from './pages/LandingPage';
import ApproachSelector from './pages/ApproachSelector';
import CultureMatch from './pages/CultureMatch';
import ProtectedRoute from './components/auth/ProtectedRoute';
import ApproachIndicator from './components/ApproachIndicator';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ApproachProvider } from './context/ApproachContext';
import { logout } from './services/authService';
import './index.css';

function Navigation() {
  const location = useLocation();
  const { currentUser } = useAuth();

  const isActive = (path) => {
    return location.pathname === path;
  };

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Failed to log out', error);
    }
  };

  return (
    <nav className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <AcademicCapIcon className="h-8 w-8 text-primary" />
              <span className="ml-2 text-xl font-bold text-gray-900">College Counselor</span>
            </div>
            <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
              <Link
                to="/profile"
                className={`${isActive('/profile')
                  ? 'border-primary text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                <DocumentTextIcon className="h-5 w-5 mr-2" />
                Student Profile
              </Link>
              <Link
                to="/chat"
                className={`${isActive('/chat')
                  ? 'border-primary text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                <ChatBubbleLeftRightIcon className="h-5 w-5 mr-2" />
                AI Counselor
              </Link>
              <Link
                to="/universities"
                className={`${isActive('/universities')
                  ? 'border-primary text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                <BuildingLibraryIcon className="h-5 w-5 mr-2" />
                UniInsight
              </Link>
              <Link
                to="/culture-match"
                className={`${isActive('/culture-match')
                  ? 'border-primary text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                <SparklesIcon className="h-5 w-5 mr-2" />
                Vibe Match
              </Link>
              <Link
                to="/launchpad"
                className={`${isActive('/launchpad')
                  ? 'border-primary text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
              >
                <RocketLaunchIcon className="h-5 w-5 mr-2" />
                My Launchpad
              </Link>
              {/* Knowledge Base - Only visible to admin */}
              {currentUser?.email === 'cvsubs@gmail.com' && (
                <Link
                  to="/knowledge-base"
                  className={`${isActive('/knowledge-base')
                    ? 'border-primary text-gray-900'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium`}
                >
                  <BookOpenIcon className="h-5 w-5 mr-2" />
                  Knowledge Base
                </Link>
              )}
            </div>
          </div>
          <div className="flex items-center">
            {currentUser && (
              <div className="flex items-center space-x-4">
                {/* Approach Indicator */}
                <ApproachIndicator />

                <div className="flex items-center space-x-2">
                  {currentUser.photoURL && (
                    <img
                      src={currentUser.photoURL}
                      alt={currentUser.displayName}
                      className="h-8 w-8 rounded-full"
                    />
                  )}
                  <span className="text-sm text-gray-700">{currentUser.displayName}</span>
                </div>
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center px-3 py-2 border border-transparent text-sm font-medium rounded-md text-gray-700 hover:bg-gray-100 transition-colors"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5 mr-1" />
                  Sign Out
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

// Layout component for protected routes
function AppLayout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <ApproachProvider>
          <Routes>
            {/* Public route */}
            <Route path="/" element={<LandingPage />} />

            {/* Approach selector (can be accessed both before and after login) */}
            <Route path="/select-approach" element={<ApproachSelector />} />

            {/* Protected routes */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route path="/profile" element={<Profile />} />
              <Route path="/chat" element={<Chat />} />
              <Route path="/universities" element={<UniversityExplorer />} />
              <Route path="/culture-match" element={<CultureMatch />} />
              <Route path="/launchpad" element={<MyLaunchpad />} />
              <Route path="/knowledge-base" element={<KnowledgeBase />} />
            </Route>
          </Routes>
        </ApproachProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
