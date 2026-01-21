import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, useLocation, Outlet } from 'react-router-dom';
import { AcademicCapIcon, DocumentTextIcon, ChartBarIcon, ChatBubbleLeftRightIcon, ArrowRightOnRectangleIcon, BookOpenIcon, BuildingLibraryIcon, SparklesIcon, RocketLaunchIcon, StarIcon } from '@heroicons/react/24/outline';
import CreditsBadge from './components/CreditsBadge';
import Profile from './pages/Profile';
import Chat from './pages/Chat';
import KnowledgeBase from './pages/KnowledgeBase';
import UniversityExplorer from './pages/UniversityExplorer';
import StratiaLaunchpad from './pages/StratiaLaunchpad';
import ApplicationsPage from './pages/ApplicationsPage';
import EssayHelpPage from './pages/EssayHelpPage';
import FitVisualizer from './pages/FitVisualizer';
import LandingPage from './pages/LandingPage';
import PricingPage from './pages/PricingPage';
import ContactPage from './pages/ContactPage';
import PaymentSuccess from './pages/PaymentSuccess';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import CounselorPage from './pages/CounselorPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import OnboardingModal from './components/OnboardingModal';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ApproachProvider } from './context/ApproachContext';
import { PaymentProvider, usePayment } from './context/PaymentContext';
import { ToastProvider } from './components/Toast';
import UpgradeModal from './components/UpgradeModal';
import { logout } from './services/authService';
import { checkOnboardingStatus, saveOnboardingProfile, fetchUserProfile, sendWelcomeEmail } from './services/api';
import ScrollToTop from './components/ScrollToTop';
import './index.css';

function Navigation() {
  const location = useLocation();
  const { currentUser } = useAuth();

  const isActive = (path) => location.pathname === path;

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Failed to log out', error);
    }
  };

  // Navigation links with Stratia styling
  const navLinks = [
    { path: '/profile', label: 'Profile', icon: DocumentTextIcon },
    { path: '/universities', label: 'Discover', icon: BuildingLibraryIcon },
    { path: '/launchpad', label: 'My Schools', icon: RocketLaunchIcon },
    { path: '/counselor', label: 'Roadmap', icon: SparklesIcon },
  ];


  return (
    <nav className="bg-[#FDFCF7]/95 backdrop-blur-sm border-b border-[#E0DED8] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex justify-between items-center h-36">
          {/* Logo */}
          <div className="flex items-center">
            <Link to="/" className="flex items-center">
              <img
                src="/logo.png"
                alt="Stratia Admissions"
                className="h-32 w-auto object-contain object-left mix-blend-multiply"
              />
            </Link>

            {/* Nav Links */}
            <div className="hidden sm:ml-8 sm:flex sm:items-center sm:gap-1">
              {navLinks.map((link) => (
                <Link
                  key={link.path}
                  to={link.path}
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2
                    ${isActive(link.path)
                      ? 'bg-[#D6E8D5] text-[#1A4D2E]'
                      : 'text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E]'
                    }`}
                >
                  <link.icon className="h-4 w-4" />
                  {link.label}
                </Link>
              ))}

              {/* Admin Knowledge Base Link */}
              {currentUser?.email === 'cvsubs@gmail.com' && (
                <Link
                  to="/knowledge-base"
                  className={`px-4 py-2 rounded-full text-sm font-medium transition-all flex items-center gap-2
                    ${isActive('/knowledge-base')
                      ? 'bg-[#D6E8D5] text-[#1A4D2E]'
                      : 'text-[#4A4A4A] hover:bg-[#F8F6F0] hover:text-[#1A4D2E]'
                    }`}
                >
                  Knowledge Base
                </Link>
              )}
            </div>
          </div>

          {/* User Menu */}
          <div className="flex items-center gap-3">
            {currentUser && (
              <>
                <div className="hidden md:flex items-center gap-2">
                  {currentUser.photoURL && (
                    <img
                      src={currentUser.photoURL}
                      alt={currentUser.displayName}
                      className="h-8 w-8 rounded-full ring-2 ring-[#D6E8D5]"
                    />
                  )}
                  <span className="text-sm text-[#4A4A4A] font-medium">
                    {currentUser.displayName}
                  </span>
                </div>
                <button
                  onClick={handleLogout}
                  className="px-3 py-2 text-sm font-medium text-[#4A4A4A] border border-[#E0DED8] rounded-full hover:bg-[#F8F6F0] hover:border-[#1A4D2E] transition-all"
                >
                  Sign Out
                </button>
                <Link
                  to="/pricing"
                  className="hidden sm:inline-flex items-center px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-full hover:bg-[#2D6B45] transition-all shadow-md"
                >
                  <StarIcon className="h-4 w-4 mr-1" />
                  Upgrade
                </Link>
              </>
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
        console.log('[App] v2 - Checking if profile exists for:', currentUser.email);

        // Use fetchUserProfile which returns both content and structured profile
        const profileResult = await fetchUserProfile(currentUser.email);
        const hasContent = profileResult.content && profileResult.content.length > 100;
        const hasStructuredProfile = profileResult.profile && Object.keys(profileResult.profile).length > 0;

        console.log('[App] v2 - Profile result:', profileResult.success, 'content length:', profileResult.content?.length || 0, 'has structured:', hasStructuredProfile);

        // If profile has content OR structured profile data, skip onboarding
        if (profileResult.success && (hasContent || hasStructuredProfile)) {
          console.log('[App] v2 - User has profile, skipping onboarding');
          sessionStorage.setItem(completedKey, 'true');
          setShowOnboarding(false);
        } else {
          console.log('[App] v2 - No profile found, showing onboarding');
          setShowOnboarding(true);

          // Send welcome email to new user (fire and forget)
          const welcomeEmailKey = `welcome_email_sent_${currentUser.email}`;
          if (!localStorage.getItem(welcomeEmailKey)) {
            console.log('[App] Sending welcome email to new user:', currentUser.email);
            sendWelcomeEmail(currentUser.email).then(result => {
              if (result.success) {
                localStorage.setItem(welcomeEmailKey, 'true');
                console.log('[App] Welcome email sent successfully');
              }
            }).catch(err => console.error('[App] Welcome email failed:', err));
          }
        }
      } catch (error) {
        console.error('[App] v2 - Error checking profile:', error);
        // On error, DON'T show onboarding - we don't want to block returning users
        setShowOnboarding(false);
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
    <div className="min-h-screen bg-[#FDFCF7]">
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
      <ScrollToTop />
      <AuthProvider>
        <PaymentProvider>
          <ApproachProvider>
            <ToastProvider>
              <Routes>
                {/* Public routes */}
                <Route path="/" element={<LandingPage />} />
                <Route path="/pricing" element={<PricingPage />} />
                <Route path="/contact" element={<ContactPage />} />
                <Route path="/payment-success" element={<PaymentSuccess />} />
                <Route path="/privacy" element={<PrivacyPolicy />} />
                <Route path="/terms" element={<TermsOfService />} />

                {/* Protected routes */}
                <Route
                  element={
                    <ProtectedRoute>
                      <AppLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route path="/profile" element={<Profile />} />
                  {/* My Advisor - DISABLED FOR MVP */}
                  {/* <Route path="/chat" element={<Chat />} /> */}
                  <Route path="/universities" element={<UniversityExplorer />} />
                  <Route path="/launchpad" element={<StratiaLaunchpad />} />
                  <Route path="/counselor" element={<CounselorPage />} />
                  <Route path="/applications" element={<ApplicationsPage />} />
                  <Route path="/essay-help/:universityId" element={<EssayHelpPage />} />
                  <Route path="/fit-visualizer" element={<FitVisualizer />} />
                  <Route path="/knowledge-base" element={<KnowledgeBase />} />
                </Route>
              </Routes>
              <UpgradeModal />
            </ToastProvider>
          </ApproachProvider>
        </PaymentProvider>
      </AuthProvider>
    </Router>
  );
}

export default App;
