import React, { useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  ArrowRightIcon,
  BookOpenIcon,
  KeyIcon,
  CheckCircleIcon,
  DocumentTextIcon,
  AcademicCapIcon,
  ChartBarIcon
} from '@heroicons/react/24/outline';
import { signInWithGoogle } from '../services/authService';
import { motion, useInView } from 'framer-motion';

// Import demo components
import OnboardingDemo from '../components/demos/OnboardingDemo';
import DocumentUploadDemo from '../components/demos/DocumentUploadDemo';
import ProfileViewDemo from '../components/demos/ProfileViewDemo';
import UniversityCardsDemo from '../components/demos/UniversityCardsDemo';
import AIChatDemo from '../components/demos/AIChatDemo';
import FitAnalysisDemo from '../components/demos/FitAnalysisDemo';
import MySchoolsDemo from '../components/demos/MySchoolsDemo';

// ============================================================================
// INTERACTIVE DEMO LANDING PAGE
// Using live demo components instead of static screenshots (GoTamil-inspired)
// ============================================================================

const FeatureDemoSection = ({
  title,
  description,
  features = [],
  demo,
  reverse = false,
  bgColor = 'bg-white'
}) => {
  const ref = useRef(null);
  const isInView = useInView(ref, { once: true, amount: 0.2 });

  return (
    <section ref={ref} className={`py-24 lg:py-32 px-6 lg:px-8 ${bgColor} overflow-hidden`}>
      <div className="max-w-7xl mx-auto">
        <div className={`grid lg:grid-cols-2 gap-12 lg:gap-20 items-center ${reverse ? 'lg:flex-row-reverse' : ''}`}>
          {/* Text Content */}
          <motion.div
            className={`${reverse ? 'lg:order-2' : ''}`}
            initial={{ opacity: 0, y: 20 }}
            animate={isInView ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.6 }}
          >
            <h2 className="font-serif text-3xl sm:text-4xl lg:text-5xl font-bold text-[#1A4D2E] leading-tight mb-6">
              {title}
            </h2>
            <p className="text-xl text-[#4A4A4A] leading-relaxed mb-6">
              {description}
            </p>

            {/* Feature list */}
            {features.length > 0 && (
              <ul className="space-y-3">
                {features.map((feature, index) => (
                  <motion.li
                    key={index}
                    initial={{ opacity: 0, x: -10 }}
                    animate={isInView ? { opacity: 1, x: 0 } : {}}
                    transition={{ delay: 0.3 + index * 0.1 }}
                    className="flex items-start gap-3"
                  >
                    <CheckCircleIcon className="h-6 w-6 text-[#2E7D32] flex-shrink-0 mt-0.5" />
                    <span className="text-lg text-[#4A4A4A]">{feature}</span>
                  </motion.li>
                ))}
              </ul>
            )}
          </motion.div>

          {/* Demo Component */}
          <div className={reverse ? 'lg:order-1' : ''}>
            {demo}
          </div>
        </div>
      </div>
    </section>
  );
};

const LandingPage = () => {
  const navigate = useNavigate();
  const { currentUser } = useAuth();
  const heroRef = useRef(null);
  const heroVisible = useInView(heroRef, { once: true });
  const statsRef = useRef(null);
  const statsVisible = useInView(statsRef, { once: true, amount: 0.3 });
  const howItWorksRef = useRef(null);
  const howItWorksVisible = useInView(howItWorksRef, { once: true, amount: 0.2 });

  const handleSignIn = async () => {
    try {
      await signInWithGoogle();
      navigate('/launchpad');
    } catch (error) {
      console.error('Sign in failed:', error);
    }
  };

  const handleGetStarted = () => {
    if (currentUser) {
      navigate('/launchpad');
    } else {
      handleSignIn();
    }
  };

  return (
    <div className="min-h-screen bg-[#FDFCF7]">
      {/* ============================================
          NAVIGATION
          ============================================ */}
      <header className="fixed top-0 left-0 right-0 z-50 bg-[#FDFCF7]/80 backdrop-blur-lg border-b border-[#E0DED8]/50">
        <div className="max-w-7xl mx-auto px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <Link to="/" className="flex items-center gap-2 group">
              {/* Book & Key Logo - matches app */}
              <div className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45] shadow-md group-hover:shadow-lg transition-shadow">
                <BookOpenIcon className="w-5 h-5 text-white absolute" style={{ top: '8px', left: '8px' }} />
                <KeyIcon className="w-4 h-4 text-[#D6E8D5] absolute" style={{ bottom: '6px', right: '6px' }} />
              </div>

              {/* Brand Text */}
              <div className="flex items-baseline gap-1">
                <span className="font-serif text-xl font-semibold text-[#1A4D2E]">Stratia</span>
                <span className="font-sans text-sm font-medium text-[#4A4A4A]">Admissions</span>
              </div>
            </Link>

            <nav className="hidden md:flex items-center gap-8">
              <Link to="/pricing" className="text-[#4A4A4A] hover:text-[#1A4D2E] text-sm font-medium transition-colors">
                Pricing
              </Link>
              {currentUser ? (
                <Link
                  to="/launchpad"
                  className="px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg hover:bg-[#2D6B45] transition-all"
                >
                  Open App
                </Link>
              ) : (
                <button
                  onClick={handleSignIn}
                  className="px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg hover:bg-[#2D6B45] transition-all"
                >
                  Get Started
                </button>
              )}
            </nav>

            <button
              onClick={handleGetStarted}
              className="md:hidden px-4 py-2 bg-[#1A4D2E] text-white text-sm font-medium rounded-lg"
            >
              Start
            </button>
          </div>
        </div>
      </header>

      {/* ============================================
          HERO SECTION
          ============================================ */}
      <section
        ref={heroRef}
        className="pt-32 pb-20 lg:pt-40 lg:pb-24 px-6 lg:px-8"
      >
        <div className="max-w-5xl mx-auto text-center">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={heroVisible ? { opacity: 1, y: 0 } : {}}
            transition={{ duration: 0.8 }}
          >
            <h1 className="font-serif text-5xl sm:text-6xl lg:text-7xl xl:text-8xl font-bold text-[#1A4D2E] leading-[1.05] tracking-tight mb-8">
              One platform.
              <br />
              <span className="text-[#4A4A4A]">Your perfect college.</span>
            </h1>
            <p className="text-xl sm:text-2xl text-[#6B6B6B] leading-relaxed mb-12 max-w-2xl mx-auto">
              Stratia is where students build their profile, discover schools, and get AI-powered
              fit analysis. All in one place.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <motion.button
                onClick={handleGetStarted}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="inline-flex items-center justify-center gap-2 px-8 py-4 bg-[#1A4D2E] text-white font-semibold rounded-xl text-lg hover:bg-[#2D6B45] transition-all shadow-lg"
              >
                Get Stratia free
                <ArrowRightIcon className="h-5 w-5" />
              </motion.button>
            </div>
          </motion.div>
        </div>
      </section>

      {/* ============================================
          STATS SECTION - Social Proof
          ============================================ */}
      <section ref={statsRef} className="py-12 px-6 lg:px-8 bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45]">
        <div className="max-w-6xl mx-auto">
          <div className="grid md:grid-cols-3 gap-8 lg:gap-12">
            {[
              { value: "1,600+", label: "Universities", sublabel: "U.S. colleges & programs" },
              { value: "100%", label: "Automated", sublabel: "Profile building from documents" },
              { value: "Real-time", label: "AI Analysis", sublabel: "Instant fit score calculation" }
            ].map((stat, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                animate={statsVisible ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: index * 0.2, duration: 0.6 }}
                className="text-center"
              >
                <div className="text-5xl lg:text-6xl font-bold text-white mb-2 font-serif">
                  {stat.value}
                </div>
                <div className="text-xl font-semibold text-[#D6E8D5] mb-1">
                  {stat.label}
                </div>
                <div className="text-sm text-[#A8C5A6]">
                  {stat.sublabel}
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================
          HOW IT WORKS SECTION
          ============================================ */}
      <section ref={howItWorksRef} className="py-16 lg:py-20 px-6 lg:px-8 bg-white">
        <div className="max-w-6xl mx-auto">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={howItWorksVisible ? { opacity: 1, y: 0 } : {}}
            className="text-center mb-16"
          >
            <h2 className="font-serif text-4xl sm:text-5xl font-bold text-[#1A4D2E] mb-4">
              How Stratia Works
            </h2>
            <p className="text-xl text-[#6B6B6B] max-w-2xl mx-auto">
              Four simple steps to find your perfect college match
            </p>
          </motion.div>

          <div className="grid md:grid-cols-4 gap-8">
            {[
              {
                step: "1",
                icon: DocumentTextIcon,
                title: "Upload & Extract",
                description: "Drop your documents. AI extracts your GPA, test scores, and activities automatically."
              },
              {
                step: "2",
                icon: AcademicCapIcon,
                title: "Build Profile",
                description: "Review your complete academic profile. Add honors, leadership roles, and achievements."
              },
              {
                step: "3",
                icon: ChartBarIcon,
                title: "Get Fit Scores",
                description: "Search 1,600+ schools. See instant fit scores comparing you to admitted students."
              },
              {
                step: "4",
                icon: CheckCircleIcon,
                title: "Build Your List",
                description: "Create a balanced list with reach, target, and safety schools. Track your applications."
              }
            ].map((item, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 30 }}
                animate={howItWorksVisible ? { opacity: 1, y: 0 } : {}}
                transition={{ delay: 0.3 + index * 0.15, duration: 0.6 }}
                className="relative"
              >
                {/* Step number */}
                <div className="absolute -top-4 -left-4 w-12 h-12 rounded-full bg-gradient-to-br from-[#FF8C42] to-[#E67A2E] flex items-center justify-center text-white font-bold text-xl shadow-lg">
                  {item.step}
                </div>

                {/* Card */}
                <div className="bg-[#F8F6F0] rounded-2xl p-6 h-full border-2 border-[#E0DED8] hover:border-[#1A4D2E] transition-all">
                  <div className="w-14 h-14 rounded-xl bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45] flex items-center justify-center mb-4">
                    <item.icon className="w-7 h-7 text-white" />
                  </div>
                  <h3 className="font-bold text-xl text-[#1A4D2E] mb-3">
                    {item.title}
                  </h3>
                  <p className="text-[#4A4A4A] leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* ============================================
          DEMO SECTIONS - Interactive components
          ============================================ */}

      <FeatureDemoSection
        title="Get started in 30 seconds."
        description="No complex forms. No endless questions. Just your name, grade, and school. That's it."
        features={[
          "Simple 4-field onboarding form",
          "Save progress and come back anytime",
          "Skip setup and explore first"
        ]}
        demo={<OnboardingDemo />}
        bgColor="bg-[#FDFCF7]"
      />

      <FeatureDemoSection
        title="Upload documents. We do the work."
        description="Drop your transcript, test scores, and activities. Our AI extracts everything automatically—no manual data entry required."
        features={[
          "Supports PDF, DOCX, TXT, and image files",
          "Extracts GPA, courses, test scores, and activities",
          "Review and edit before finalizing",
          "Processing takes seconds, not hours"
        ]}
        demo={<DocumentUploadDemo />}
        reverse={true}
        bgColor="bg-white"
      />

      <FeatureDemoSection
        title="See your full academic profile."
        description="Everything in one place—academics, test scores, activities, and awards. Know exactly what colleges will see."
        features={[
          "Complete academic snapshot at a glance",
          "Track all honors, AP, and IB courses",
          "Showcase leadership roles and impact",
          "Highlight awards and achievements"
        ]}
        demo={<ProfileViewDemo />}
        bgColor="bg-[#FDFCF7]"
      />

      <FeatureDemoSection
        title="Discover 1,600+ universities."
        description="Browse schools with real acceptance rates, rankings, and costs. Filter by location, major, or selectivity. Every school in one search."
        features={[
          "Search across 1,600+ U.S. universities",
          "Filter by state, major, size, and cost",
          "See acceptance rates and rankings",
          "Compare tuition and financial aid"
        ]}
        demo={<UniversityCardsDemo />}
        reverse={true}
        bgColor="bg-white"
      />

      <FeatureDemoSection
        title="Ask anything about any school."
        description="Our AI knows about majors, career outcomes, campus culture, and application strategies. Get instant answers with sources."
        features={[
          "Ask about specific programs and majors",
          "Learn about campus culture and student life",
          "Get application tips and deadlines",
          "Understand career outcomes and salaries"
        ]}
        demo={<AIChatDemo />}
        bgColor="bg-[#FDFCF7]"
      />

      <FeatureDemoSection
        title="Track your balanced school list."
        description="Save schools and see your match score for each one. Stratia compares your profile to admitted students and calculates your fit."
        features={[
          "Instant fit score for every school",
          "Automatic reach/target/safety categorization",
          "Track application deadlines",
          "Visual list breakdown"
        ]}
        demo={<MySchoolsDemo />}
        reverse={true}
        bgColor="bg-white"
      />

      <FeatureDemoSection
        title="Data-driven recommendations."
        description="See exactly why each school is a reach, target, or safety. No vague guesses—just clear data comparing your stats to admitted students."
        features={[
          "Detailed score breakdown by category",
          "Side-by-side comparison with admitted students",
          "Specific improvement recommendations",
          "Honest assessment you can trust"
        ]}
        demo={<FitAnalysisDemo />}
        bgColor="bg-[#FDFCF7]"
      />

      {/* ============================================
          FINAL CTA
          ============================================ */}
      <section className="py-32 px-6 lg:px-8 bg-[#1A4D2E]">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="font-serif text-4xl sm:text-5xl lg:text-6xl font-bold text-white leading-tight mb-8">
            Ready to find your
            <br />
            perfect college?
          </h2>
          <p className="text-xl text-[#D6E8D5] mb-12">
            Join students who are taking control of their college journey.
          </p>
          <motion.button
            onClick={handleGetStarted}
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            className="inline-flex items-center justify-center gap-2 px-10 py-5 bg-white text-[#1A4D2E] font-bold rounded-xl text-xl hover:bg-[#F8F6F0] transition-all shadow-xl"
          >
            Get started free
            <ArrowRightIcon className="h-6 w-6" />
          </motion.button>
          <p className="text-[#A8C5A6] mt-8 text-sm">
            Free tier available • No credit card required
          </p>
        </div>
      </section>

      {/* ============================================
          FOOTER
          ============================================ */}
      <footer className="py-12 px-6 lg:px-8 bg-[#0D2818] text-white">
        <div className="max-w-7xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <Link to="/" className="flex items-center gap-2">
              <div className="relative w-10 h-10 flex items-center justify-center rounded-xl bg-gradient-to-br from-[#1A4D2E] to-[#2D6B45]">
                <BookOpenIcon className="w-5 h-5 text-white absolute" style={{ top: '8px', left: '8px' }} />
                <KeyIcon className="w-4 h-4 text-[#D6E8D5] absolute" style={{ bottom: '6px', right: '6px' }} />
              </div>
              <div className="flex items-baseline gap-1">
                <span className="font-serif text-lg font-semibold">Stratia</span>
                <span className="text-xs text-[#A8C5A6] font-medium">Admissions</span>
              </div>
            </Link>

            <div className="flex gap-8 text-sm text-[#A8C5A6]">
              <Link to="/pricing" className="hover:text-white transition-colors">Pricing</Link>
              <Link to="/privacy-policy" className="hover:text-white transition-colors">Privacy</Link>
              <Link to="/terms-of-service" className="hover:text-white transition-colors">Terms</Link>
            </div>
          </div>

          <div className="mt-8 pt-8 border-t border-white/10 text-center text-sm text-[#6B8F6B]">
            © {new Date().getFullYear()} Stratia Admissions
          </div>
        </div>
      </footer>
    </div>
  );
};

export default LandingPage;
