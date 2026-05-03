import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link, Navigate, useLocation, Outlet } from 'react-router-dom';
import { AcademicCapIcon, DocumentTextIcon, ChartBarIcon, ChatBubbleLeftRightIcon, ArrowRightOnRectangleIcon, BookOpenIcon, BuildingLibraryIcon, SparklesIcon, RocketLaunchIcon, StarIcon } from '@heroicons/react/24/outline';
import ResourcesPage from './pages/ResourcesPage';
import ResourcePaperPage from './pages/ResourcePaperPage';
import QaRunsListPage from './pages/QaRunsListPage';
import QaRunDetailPage from './pages/QaRunDetailPage';
import AdminGate from './components/qa/AdminGate';
import CreditsBadge from './components/CreditsBadge';
import Profile from './pages/Profile';
import Chat from './pages/Chat';
import KnowledgeBase from './pages/KnowledgeBase';
import UniversityExplorer from './pages/UniversityExplorer';
import StratiaLaunchpad from './pages/StratiaLaunchpad';
import EssayHelpPage from './pages/EssayHelpPage';
import FitVisualizer from './pages/FitVisualizer';
import LandingPage from './pages/LandingPage';
import PricingPage from './pages/PricingPage';
import ContactPage from './pages/ContactPage';
import PaymentSuccess from './pages/PaymentSuccess';
import PrivacyPolicy from './pages/PrivacyPolicy';
import TermsOfService from './pages/TermsOfService';
import FinancialAidComparison from './pages/FinancialAidComparison';
import RoadmapPage from './pages/RoadmapPage';
import ProtectedRoute from './components/auth/ProtectedRoute';
import Navigation from './components/Navigation';
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

// Navigation lives in components/Navigation.jsx — a single auth-aware
// component shared by AppLayout (protected pages) and the public Resources
// routes. Logged-out visitors see only the Resources link + a Try Stratia
// CTA; signed-in users see the full nav.

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
                {/* Resources & whitepapers — public so prospective users
                    (parents, counselors) can find them without signing in. */}
                <Route path="/resources" element={<ResourcesPage />} />
                <Route path="/resources/:slug" element={<ResourcePaperPage />} />

                {/* QA admin dashboard — INTERNAL ONLY. AdminGate renders a
                    404 (not a 403) for any non-admin or signed-out visitor
                    so the route is invisible to customers. There is NO nav
                    entry anywhere in the app pointing here. Access is
                    via direct URL only. Firestore security rules are the
                    hard gate at the data layer. */}
                <Route
                  path="/qa-runs"
                  element={<AdminGate><QaRunsListPage /></AdminGate>}
                />
                <Route
                  path="/qa-runs/:runId"
                  element={<AdminGate><QaRunDetailPage /></AdminGate>}
                />

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
                  <Route path="/roadmap" element={<RoadmapPage />} />
                  {/* Legacy routes redirect to the corresponding inner tab on
                      the consolidated /roadmap surface. `replace` on the
                      Navigate so back-button doesn't bounce between the old
                      and new URL. Query strings on legacy URLs are dropped
                      intentionally — there are no callers in the codebase
                      relying on them. */}
                  <Route path="/counselor" element={<Navigate to="/roadmap?tab=plan" replace />} />
                  <Route path="/progress" element={<Navigate to="/roadmap?tab=essays" replace />} />
                  <Route path="/essays" element={<Navigate to="/roadmap?tab=essays" replace />} />
                  <Route path="/applications" element={<Navigate to="/roadmap?tab=colleges" replace />} />
                  <Route path="/essay-help/:universityId" element={<EssayHelpPage />} />
                  <Route path="/fit-visualizer" element={<FitVisualizer />} />
                  <Route path="/knowledge-base" element={<KnowledgeBase />} />
                  <Route path="/financial-aid" element={<FinancialAidComparison />} />
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
