import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Outlet } from 'react-router-dom';
import { AcademicCapIcon, DocumentTextIcon, ChartBarIcon, ChatBubbleLeftRightIcon, ArrowRightOnRectangleIcon, BookOpenIcon, BuildingLibraryIcon, SparklesIcon, RocketLaunchIcon, StarIcon } from '@heroicons/react/24/outline';
import CreditsBadge from './components/CreditsBadge';
import Profile from './pages/Profile';
import Chat from './pages/Chat';
import KnowledgeBase from './pages/KnowledgeBase';
import UniversityExplorer from './pages/UniversityExplorer';
import MyLaunchpad from './pages/MyLaunchpad';
import FitVisualizer from './pages/FitVisualizer';
import LandingPage from './pages/LandingPage';
import PricingPage from './pages/PricingPage';
import ContactPage from './pages/ContactPage';
import PaymentSuccess from './pages/PaymentSuccess';
import ProtectedRoute from './components/auth/ProtectedRoute';
import OnboardingModal from './components/OnboardingModal';
import ApproachIndicator from './components/ApproachIndicator';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ApproachProvider } from './context/ApproachContext';
import { PaymentProvider, usePayment } from './context/PaymentContext';
import UpgradeModal from './components/UpgradeModal';
import { logout } from './services/authService';
import { checkOnboardingStatus, saveOnboardingProfile } from './services/api';
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
    <nav className="bg-white/90 backdrop-blur-sm shadow-sm border-b border-amber-100 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between h-16">
          <div className="flex">
            <div className="flex-shrink-0 flex items-center">
              <div className="p-1.5 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl shadow-lg shadow-amber-200">
                <SparklesIcon className="h-6 w-6 text-white" />
              </div>
              <span className="ml-2 text-xl font-bold bg-gradient-to-r from-amber-600 to-orange-600 bg-clip-text text-transparent">CollegeAI Pro</span>
            </div>
            <div className="hidden sm:ml-8 sm:flex sm:space-x-6">
              <Link
                to="/profile"
                className={`${isActive('/profile')
                  ? 'border-amber-500 text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-amber-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
              >
                <DocumentTextIcon className="h-5 w-5 mr-2" />
                Student Profile
              </Link>
              <Link
                to="/chat"
                className={`${isActive('/chat')
                  ? 'border-amber-500 text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-amber-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
              >
                <ChatBubbleLeftRightIcon className="h-5 w-5 mr-2" />
                My Advisor
              </Link>
              <Link
                to="/universities"
                className={`${isActive('/universities')
                  ? 'border-amber-500 text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-amber-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
              >
                <BuildingLibraryIcon className="h-5 w-5 mr-2" />
                UniInsight
              </Link>
              <Link
                to="/launchpad"
                className={`${isActive('/launchpad')
                  ? 'border-amber-500 text-gray-900'
                  : 'border-transparent text-gray-500 hover:border-amber-300 hover:text-gray-700'
                  } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
              >
                <RocketLaunchIcon className="h-5 w-5 mr-2" />
                My Launchpad
              </Link>
              {/* Knowledge Base - Only visible to admin */}
              {currentUser?.email === 'cvsubs@gmail.com' && (
                <Link
                  to="/knowledge-base"
                  className={`${isActive('/knowledge-base')
                    ? 'border-amber-500 text-gray-900'
                    : 'border-transparent text-gray-500 hover:border-amber-300 hover:text-gray-700'
                    } inline-flex items-center px-1 pt-1 border-b-2 text-sm font-medium transition-colors`}
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
                <div className="flex items-center space-x-2">
                  {currentUser.photoURL && (
                    <img
                      src={currentUser.photoURL}
                      alt={currentUser.displayName}
                      className="h-8 w-8 rounded-full ring-2 ring-amber-100"
                    />
                  )}
                  <span className="text-sm text-gray-700 font-medium">{currentUser.displayName}</span>
                </div>
                <CreditsBadge compact />
                <button
                  onClick={handleLogout}
                  className="inline-flex items-center px-3 py-2 border border-gray-200 text-sm font-medium rounded-xl text-gray-700 hover:bg-amber-50 hover:border-amber-200 transition-colors"
                >
                  <ArrowRightOnRectangleIcon className="h-5 w-5 mr-1" />
                  Sign Out
                </button>
                <Link
                  to="/pricing"
                  className="inline-flex items-center px-3 py-2 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-sm font-medium rounded-xl hover:from-amber-400 hover:to-orange-400 transition-all shadow-md hover:shadow-lg"
                >
                  <StarIcon className="h-5 w-5 mr-1" />
                  Upgrade
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}

// Layout component for protected routes with onboarding
function AppLayout() {
  const { currentUser } = useAuth();
  const [showOnboarding, setShowOnboarding] = useState(false);
  const [onboardingChecked, setOnboardingChecked] = useState(false);

  // Check onboarding status on mount
  useEffect(() => {
    const checkOnboarding = async () => {
      if (!currentUser?.email) return;

      // Only skip if user already completed or explicitly skipped onboarding
      const completedKey = `onboarding_completed_${currentUser.email}`;
      const skippedKey = `onboarding_skipped_${currentUser.email}`;

      if (sessionStorage.getItem(completedKey) || sessionStorage.getItem(skippedKey)) {
        console.log('[App] Onboarding already completed/skipped this session');
        setOnboardingChecked(true);
        return;
      }

      try {
        console.log('[App] Checking onboarding status for:', currentUser.email);
        const status = await checkOnboardingStatus(currentUser.email);
        console.log('[App] Onboarding status result:', status);

        if (status.needsOnboarding) {
          console.log('[App] User needs onboarding, showing modal');
          setShowOnboarding(true);
        } else {
          console.log('[App] User already onboarded, skipping modal');
          // Mark as completed so we don't check again this session
          sessionStorage.setItem(completedKey, 'true');
        }
      } catch (error) {
        console.error('[App] Error checking onboarding:', error);
        // On error, show onboarding to be safe
        setShowOnboarding(true);
      }
      setOnboardingChecked(true);
    };

    checkOnboarding();
  }, [currentUser?.email]);

  const handleOnboardingComplete = async (profileData) => {
    try {
      console.log('[App] Onboarding complete, saving profile...');
      const result = await saveOnboardingProfile(currentUser.email, profileData);
      console.log('[App] Profile saved:', result);

      // Mark as completed
      sessionStorage.setItem(`onboarding_completed_${currentUser.email}`, 'true');
      setShowOnboarding(false);
    } catch (error) {
      console.error('[App] Error saving onboarding profile:', error);
      setShowOnboarding(false);
    }
  };

  const handleOnboardingSkip = () => {
    console.log('[App] User skipped onboarding');
    // Mark as skipped in session
    sessionStorage.setItem(`onboarding_skipped_${currentUser.email}`, 'true');
    setShowOnboarding(false);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 via-white to-orange-50">
      <Navigation />
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <Outlet />
      </main>

      {/* Onboarding Modal */}
      <OnboardingModal
        isOpen={showOnboarding}
        onComplete={handleOnboardingComplete}
        onSkip={handleOnboardingSkip}
        userEmail={currentUser?.email}
      />
    </div>
  );
}

function App() {
  return (
    <Router>
      <AuthProvider>
        <PaymentProvider>
          <ApproachProvider>
            <Routes>
              {/* Public routes */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/pricing" element={<PricingPage />} />
              <Route path="/contact" element={<ContactPage />} />
              <Route path="/payment-success" element={<PaymentSuccess />} />

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
                <Route path="/launchpad" element={<MyLaunchpad />} />
                <Route path="/fit-visualizer" element={<FitVisualizer />} />
                <Route path="/knowledge-base" element={<KnowledgeBase />} />
              </Route>
            </Routes>
            <UpgradeModal />
          </ApproachProvider>
        </PaymentProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
