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
  ChartBarIcon,
  PencilSquareIcon,
  SparklesIcon
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
import FitChatDemo from '../components/demos/FitChatDemo';
import EssayHelpDemo from '../components/demos/EssayHelpDemo';

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
        <div className={`grid lg:grid-cols-2 gap-12 lg:gap-20 items-start ${reverse ? 'lg:flex-row-reverse' : ''}`}>
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
              <span className="text-[#4A4A4A]">Your dream college.</span>
            </h1>
            <p className="text-xl sm:text-2xl text-[#6B6B6B] leading-relaxed mb-12 max-w-2xl mx-auto">
              Build your profile, discover schools where you'll thrive, and apply with a strategy that actually works.
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
              { value: "200+", label: "Top Universities", sublabel: "Curated deep-dive profiles" },
              { value: "100%", label: "Holistic", sublabel: "Story-driven profile building" },
              { value: "4-Year", label: "Journey", sublabel: "Freshman to Senior guidance" }
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
          PAIN POINTS SECTION - The Real Problem
          ============================================ */}
      <section className="py-20 lg:py-28 px-6 lg:px-8 bg-[#FDFCF7]">
        <div className="max-w-5xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="font-serif text-4xl sm:text-5xl font-bold text-[#1A4D2E] mb-6">
              College Admissions is a Multi-Dimensional Puzzle.
              <br />
              <span className="text-[#4A4A4A]">Stratia Connects the Dots.</span>
            </h2>
            <p className="text-xl text-[#6B6B6B] max-w-3xl mx-auto">
              Finding the right <strong>colleges</strong>, discovering <strong>majors</strong> that fit,
              identifying every dimension of your <strong>profile</strong>, and weaving it all into
              a <strong>compelling narrative</strong>—this is the real challenge. Most students have the
              pieces, but don't know how to connect them.
            </p>
          </div>

          <div className="grid md:grid-cols-2 lg:grid-cols-3 gap-8">
            {/* Pain Point 1 */}
            <div className="bg-white rounded-2xl p-8 border-2 border-red-100 shadow-sm">
              <div className="text-4xl mb-4">😰</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                "I Forgot Half My Activities"
              </h3>
              <p className="text-gray-600 leading-relaxed">
                By senior year, students scramble to remember freshman and sophomore achievements.
                Leadership roles, volunteer hours, and awards slip through the cracks.
              </p>
            </div>

            {/* Pain Point 2 */}
            <div className="bg-white rounded-2xl p-8 border-2 border-red-100 shadow-sm">
              <div className="text-4xl mb-4">⏰</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                "I Waited Until the Last Minute"
              </h3>
              <p className="text-gray-600 leading-relaxed">
                College prep is a 4-year journey, not a senior-year sprint. Last-minute cramming
                produces applications that feel rushed and inauthentic.
              </p>
            </div>

            {/* Pain Point 3 */}
            <div className="bg-white rounded-2xl p-8 border-2 border-red-100 shadow-sm">
              <div className="text-4xl mb-4">🧩</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                "I Have the Pieces, But No Story"
              </h3>
              <p className="text-gray-600 leading-relaxed">
                You have experiences and achievements—but weaving them into a cohesive narrative
                that resonates with admissions officers is the real challenge.
              </p>
            </div>

            {/* Pain Point 4 */}
            <div className="bg-white rounded-2xl p-8 border-2 border-red-100 shadow-sm">
              <div className="text-4xl mb-4">📋</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                "I Don't Know What Matters"
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Should you list 10 activities or 3 deep ones? Does that summer job count?
                Without guidance, students leave out meaningful experiences.
              </p>
            </div>

            {/* Pain Point 5 */}
            <div className="bg-white rounded-2xl p-8 border-2 border-red-100 shadow-sm">
              <div className="text-4xl mb-4">⚖️</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                "My List is 90% Reach Schools"
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Without data, students fall in love with dream schools and forget to build a
                balanced Reach / Target / Safety list based on real admission data.
              </p>
            </div>

            {/* Pain Point 6 */}
            <div className="bg-white rounded-2xl p-8 border-2 border-red-100 shadow-sm">
              <div className="text-4xl mb-4">💸</div>
              <h3 className="text-xl font-bold text-gray-900 mb-3">
                "I Can't Afford a Counselor"
              </h3>
              <p className="text-gray-600 leading-relaxed">
                Private college counselors cost $5,000–$10,000+. Most families can't afford
                personalized guidance, leaving students to figure it out alone.
              </p>
            </div>
          </div>

          {/* Solution Teaser - Expanded */}
          <div className="mt-16 bg-[#1A4D2E] rounded-3xl p-8 lg:p-12">
            <div className="text-center mb-8">
              <div className="inline-flex items-center gap-2 px-4 py-2 bg-white/10 text-white rounded-full text-sm font-medium mb-4">
                <SparklesIcon className="h-4 w-4" />
                How Stratia Solves This
              </div>
              <h3 className="text-3xl lg:text-4xl font-bold text-white mb-4">
                100+ Data Points. One Clear Fit Score.
              </h3>
              <p className="text-xl text-[#D6E8D5] max-w-3xl mx-auto">
                We analyze <strong>100+ data points per university</strong>—including GPA ranges,
                test scores, acceptance rates, demographics, essay requirements, and financial
                aid—then compare them against your profile to generate a transparent Fit Score.
              </p>
            </div>

            <div className="grid md:grid-cols-3 gap-6 text-center">
              <div className="bg-white/10 rounded-xl p-6">
                <div className="text-4xl font-bold text-white mb-2">Reach</div>
                <p className="text-[#A8C5A6] text-sm">Schools where you're below the typical admitted student stats</p>
              </div>
              <div className="bg-white/10 rounded-xl p-6">
                <div className="text-4xl font-bold text-white mb-2">Target</div>
                <p className="text-[#A8C5A6] text-sm">Schools where your profile aligns well with admitted students</p>
              </div>
              <div className="bg-white/10 rounded-xl p-6">
                <div className="text-4xl font-bold text-white mb-2">Safety</div>
                <p className="text-[#A8C5A6] text-sm">Schools where you exceed typical admitted student profiles</p>
              </div>
            </div>

            <p className="text-center text-[#D6E8D5] mt-8 text-sm">
              Every score is fully transparent—see exactly why a school is a Reach, Target, or Safety,
              and chat with AI to understand what you can improve.
            </p>
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
              Five simple steps to find your perfect college match
            </p>
          </motion.div>

          <div className="grid md:grid-cols-5 gap-6">
            {[
              {
                step: "1",
                icon: DocumentTextIcon,
                title: "Upload & Extract",
                description: "Drop transcripts, test scores, or activity lists. AI extracts everything in seconds."
              },
              {
                step: "2",
                icon: AcademicCapIcon,
                title: "Build Profile",
                description: "Review your academics, activities, and achievements. Edit anything before moving on."
              },
              {
                step: "3",
                icon: ChartBarIcon,
                title: "Get Fit Scores",
                description: "Search 1,600+ schools. Instantly see how you compare to admitted students."
              },
              {
                step: "4",
                icon: CheckCircleIcon,
                title: "Build Your List",
                description: "Save reach, target, and safety schools. Track deadlines and application status."
              },
              {
                step: "5",
                icon: PencilSquareIcon,
                title: "Perfect Your Narrative",
                description: "Find your authentic voice. Get AI guidance to turn your unique experiences into essays that stand out."
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
          "Weaves scattered docs into a cohesive story",
          "Identify gaps in your narrative early",
          "Processing takes seconds, not hours"
        ]}
        demo={<DocumentUploadDemo />}
        reverse={true}
        bgColor="bg-white"
      />

      <FeatureDemoSection
        title="Visualize your 4-year growth."
        description="Don't leave it to the last minute. Track your development from freshman year to application day. See how your activities and achievements stack up over time."
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
        title="Explore 200+ top universities."
        description="Go beyond rankings. Understand the culture, curriculum, and 'vibe' of each school to find where your story fits best."
        features={[
          "Search by name, state, major, or ranking",
          "See detailed academic programs and professors",
          "Compare acceptance rates, tuition, and ROI",
          "View campus photos and student demographics"
        ]}
        demo={<UniversityCardsDemo />}
        reverse={true}
        bgColor="bg-white"
      />

      <FeatureDemoSection
        title="Ask anything about any school."
        description="Chat with an AI that knows every school in our database. Ask about majors, professors, research opportunities, career outcomes, and admissions strategies."
        features={[
          "Get answers grounded in real university data",
          "Learn about specific programs and professors",
          "Understand application deadlines and requirements",
          "Compare schools side-by-side with AI insights"
        ]}
        demo={<AIChatDemo />}
        bgColor="bg-[#FDFCF7]"
      />

      <FeatureDemoSection
        title="Build your balanced list."
        description="Save schools and instantly see where you stand. Stratia compares your GPA, test scores, and activities to admitted students and categorizes each school."
        features={[
          "Instant fit score comparing you to admits",
          "Automatic reach/target/safety categories",
          "Track deadlines and application progress",
          "One-click access to essay help for each school"
        ]}
        demo={<MySchoolsDemo />}
        reverse={true}
        bgColor="bg-white"
      />

      <FeatureDemoSection
        title="Your AI writing partner."
        description="The Essay Workshop guides you from blank page to polished narrative. Brainstorm with guided questions, find your unique 'hook', and craft a story that admissions officers remember."
        features={[
          "Guiding questions to spark your thinking",
          "AI-generated essay starters tailored to you",
          "Real-time feedback with authenticity scores",
          "Save drafts, track versions, and iterate"
        ]}
        demo={<EssayHelpDemo />}
        bgColor="bg-[#FDFCF7]"
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


      <FeatureDemoSection
        title="Chat about your college fit."
        description="Ask specific questions about your chances, application strategy, and what you can improve. Get personalized advice based on your profile."
        features={[
          "Compare your stats to admitted students",
          "Get honest reach/target/safety assessments",
          "Learn about early decision vs. regular",
          "Understand what to improve for better chances"
        ]}
        demo={<FitChatDemo />}
        bgColor="bg-white"
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
              <Link to="/privacy" className="hover:text-white transition-colors">Privacy Policy</Link>
              <Link to="/terms" className="hover:text-white transition-colors">Terms of Service</Link>
              <Link to="/contact" className="hover:text-white transition-colors">Contact</Link>
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
