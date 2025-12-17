import { useState, useEffect, useRef } from 'react';
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  ArrowPathIcon,
  InformationCircleIcon,
  SparklesIcon,
  LockClosedIcon
} from '@heroicons/react/24/outline';
import { Link } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeRaw from 'rehype-raw';
import { startSession, sendMessage, extractFullResponse } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { usePayment } from '../context/PaymentContext';

function Chat() {
  const { currentUser } = useAuth();
  const { aiMessagesAvailable, aiMessagesLimit, consumeAiMessage, promptUpgrade, isFreeTier, hasActiveSubscription } = usePayment();

  // Initialize messages from localStorage to prevent clearing on tab switch
  const [messages, setMessages] = useState(() => {
    try {
      const savedMessages = localStorage.getItem('chatMessages');
      return savedMessages ? JSON.parse(savedMessages) : [];
    } catch (e) {
      console.error('Error loading messages from localStorage:', e);
      return [];
    }
  });

  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const [sessionId, setSessionId] = useState(null); // Track session ID
  const messagesEndRef = useRef(null);

  // Save messages to localStorage whenever they change
  useEffect(() => {
    if (messages.length > 0) {
      localStorage.setItem('chatMessages', JSON.stringify(messages));
      console.log('[Chat] Saved', messages.length, 'messages to localStorage');
    } else {
      // Only remove if explicitly cleared (not on initial mount)
      const savedMessages = localStorage.getItem('chatMessages');
      if (savedMessages && messages.length === 0) {
        console.log('[Chat] Messages cleared, keeping localStorage for persistence');
      }
    }
  }, [messages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Clear messages and session when user signs out
  useEffect(() => {
    if (!currentUser) {
      setMessages([]);
      setError(null);
      setSessionId(null);
    }
  }, [currentUser]);

  const handleSendMessage = async (e) => {
    e.preventDefault();

    if (!inputMessage.trim() || sending) return;

    // Check message limit (unless unlimited)
    if (aiMessagesAvailable !== 'unlimited' && aiMessagesAvailable <= 0) {
      promptUpgrade('ai_messages', 'You\'ve used all your AI counselor messages');
      return;
    }

    const userMessage = inputMessage.trim();
    setInputMessage('');
    setSending(true);
    setError(null);

    // Add user message to chat
    const newMessages = [...messages, { role: 'user', content: userMessage }];
    setMessages(newMessages);

    try {
      // Construct query that emphasizes knowledge base usage
      const knowledgeBaseQuery = `Please answer the following question using ONLY information from the college admissions knowledge base. Do not use general knowledge. If the information is not in the knowledge base, say so.

Question: ${userMessage}`;

      let response;

      // First message: create session
      if (!sessionId) {
        console.log('[Chat] Creating new session (first message)');
        response = await startSession(knowledgeBaseQuery, currentUser?.email);
        // Store session ID for subsequent messages - API returns 'id' not 'sessionId'
        const newSessionId = response.id || response.sessionId;
        if (newSessionId) {
          setSessionId(newSessionId);
          console.log('[Chat] Session created:', newSessionId);
        } else {
          console.error('[Chat] No session ID in response:', response);
        }
      } else {
        // Subsequent messages: use existing session, pass history
        console.log('[Chat] Sending message to existing session:', sessionId);
        response = await sendMessage(sessionId, knowledgeBaseQuery, currentUser?.email, newMessages);
      }

      // Extract response text and suggested questions
      const { result, suggested_questions } = extractFullResponse(response);

      // Update suggested questions
      if (suggested_questions && Array.isArray(suggested_questions)) {
        setSuggestedQuestions(suggested_questions);
      }

      // Add assistant response to chat
      setMessages([...newMessages, { role: 'assistant', content: result }]);

      // Consume a message credit (local tracking)
      consumeAiMessage();
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to send message. Please try again.');
      // Remove user message on error
      setMessages(messages);
    } finally {
      setSending(false);
    }
  };

  const handleNewChat = () => {
    setMessages([]);
    setError(null);
    setSuggestedQuestions([]);
    setSessionId(null); // Clear session ID for new chat
    localStorage.removeItem('chatMessages');
  };

  const handleSuggestedQuestion = async (question) => {
    if (sending) return;

    setSending(true);
    setError(null);

    // Add user message to chat
    const newMessages = [...messages, { role: 'user', content: question }];
    setMessages(newMessages);

    try {
      // Construct query that emphasizes knowledge base usage
      const knowledgeBaseQuery = `Please answer the following question using ONLY information from the college admissions knowledge base. Do not use general knowledge. If the information is not in the knowledge base, say so.

Question: ${question}`;

      let response;

      // First message: create session
      if (!sessionId) {
        console.log('[Chat] Creating new session (suggested question - first message)');
        response = await startSession(knowledgeBaseQuery, currentUser?.email);
        // Store session ID for subsequent messages - API returns 'id' not 'sessionId'
        const newSessionId = response.id || response.sessionId;
        if (newSessionId) {
          setSessionId(newSessionId);
          console.log('[Chat] Session created:', newSessionId);
        } else {
          console.error('[Chat] No session ID in response:', response);
        }
      } else {
        // Subsequent messages: use existing session, pass history
        console.log('[Chat] Sending suggested question to existing session:', sessionId);
        response = await sendMessage(sessionId, knowledgeBaseQuery, currentUser?.email, newMessages);
      }

      // Extract response text and suggested questions
      const { result, suggested_questions } = extractFullResponse(response);

      // Update suggested questions
      if (suggested_questions && Array.isArray(suggested_questions)) {
        setSuggestedQuestions(suggested_questions);
      }

      // Add assistant response to chat
      setMessages([...newMessages, { role: 'assistant', content: result }]);
    } catch (err) {
      console.error('Error sending message:', err);
      setError('Failed to send message. Please try again.');
      // Remove user message on error
      setMessages(messages);
    } finally {
      setSending(false);
    }
  };

  // Generic suggested questions for initial load - mix of general and personalized
  const defaultSuggestedQuestions = [
    "What universities offer business programs?",
    "Compare UCLA and UC Berkeley for computer science",
    "What are my chances at USC?",
    "Help me build a balanced college list"
  ];

  // Display suggested questions - use dynamic ones if available, otherwise defaults
  const displayedQuestions = suggestedQuestions.length > 0 ? suggestedQuestions : defaultSuggestedQuestions;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">My Advisor</h1>
        <p className="mt-2 text-gray-600">
          Ask anything - from general college research to personalized admissions strategy.
          I'll use your profile when relevant and search my knowledge base to provide tailored guidance.
        </p>
      </div>

      {/* Monthly Usage Indicator */}
      <div className="flex items-center justify-between bg-white rounded-2xl p-4 border border-gray-100 shadow-sm">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <ChatBubbleLeftRightIcon className="h-5 w-5 text-amber-500" />
            <span className="text-sm font-medium text-gray-700">Monthly Messages</span>
          </div>
          {hasActiveSubscription ? (
            <span className="px-3 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-bold rounded-full">
              ✨ {aiMessagesAvailable}/{aiMessagesLimit}
            </span>
          ) : (
            <div className="flex items-center gap-3">
              <div className="flex items-center gap-2">
                <div className="w-32 h-2 bg-gray-200 rounded-full overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all ${aiMessagesAvailable <= 5 ? 'bg-red-500' :
                      aiMessagesAvailable <= 10 ? 'bg-amber-500' : 'bg-green-500'
                      }`}
                    style={{ width: `${(aiMessagesAvailable / aiMessagesLimit) * 100}%` }}
                  />
                </div>
                <span className={`text-sm font-bold ${aiMessagesAvailable <= 5 ? 'text-red-600' :
                  aiMessagesAvailable <= 10 ? 'text-amber-600' : 'text-gray-700'
                  }`}>
                  {aiMessagesAvailable}/{aiMessagesLimit}
                </span>
              </div>
              {aiMessagesAvailable <= 10 && (
                <Link
                  to="/pricing"
                  className="px-3 py-1 bg-gradient-to-r from-amber-500 to-orange-500 text-white text-xs font-bold rounded-full hover:from-amber-400 hover:to-orange-400 transition-all"
                >
                  Upgrade →
                </Link>
              )}
            </div>
          )}
        </div>
        <span className="text-xs text-gray-400">Resets monthly</span>
      </div>

      {/* Chat Container */}
      <div className="bg-white shadow-lg shadow-amber-100 rounded-2xl flex flex-col border border-gray-100" style={{ height: '600px' }}>
        {/* Chat Header */}
        <div className="px-6 py-4 border-b border-amber-100 flex items-center justify-between">
          <div className="flex items-center">
            <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-xl mr-3">
              <ChatBubbleLeftRightIcon className="h-5 w-5 text-white" />
            </div>
            <h2 className="text-lg font-semibold text-gray-900">Ask me anything about colleges</h2>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleNewChat}
              className="text-sm text-gray-600 hover:text-amber-600 font-medium transition-colors"
            >
              New Chat
            </button>
          )}
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <div className="p-4 bg-gradient-to-br from-amber-100 to-orange-100 rounded-2xl inline-block mb-4">
                <SparklesIcon className="h-10 w-10 text-amber-600" />
              </div>
              <h3 className="text-lg font-medium text-gray-900 mb-2">Start a Conversation</h3>
              <p className="text-gray-600 mb-6">Ask any question about college admissions</p>

              {/* Suggested Questions */}
              <div className="max-w-2xl mx-auto">
                <p className="text-sm font-medium text-gray-700 mb-3">💡 Suggested questions:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {displayedQuestions.map((question, index) => {
                    // Color code buttons based on index
                    const colorClasses = [
                      'bg-amber-50 border-amber-200 hover:bg-amber-100 hover:border-amber-300 text-amber-900',
                      'bg-emerald-50 border-emerald-200 hover:bg-emerald-100 hover:border-emerald-300 text-emerald-900',
                      'bg-blue-50 border-blue-200 hover:bg-blue-100 hover:border-blue-300 text-blue-900',
                      'bg-purple-50 border-purple-200 hover:bg-purple-100 hover:border-purple-300 text-purple-900'
                    ];

                    return (
                      <button
                        key={index}
                        onClick={() => handleSuggestedQuestion(question)}
                        className={`text-left px-4 py-3 rounded-xl text-sm transition-all border hover:-translate-y-0.5 ${colorClasses[index % 4]}`}
                      >
                        {question}
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-3xl rounded-2xl px-4 py-3 ${message.role === 'user'
                      ? 'bg-gradient-to-r from-amber-500 to-orange-500 text-white shadow-md'
                      : 'bg-gray-50 text-gray-900 border border-gray-100'
                      }`}
                  >
                    {message.role === 'user' ? (
                      <p className="text-sm">{message.content}</p>
                    ) : (
                      <div className="prose prose-sm max-w-none prose-blue">
                        <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeRaw]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {sending && (
                <div className="flex justify-start">
                  <div className="bg-amber-50 rounded-2xl px-4 py-3 border border-amber-100">
                    <div className="flex items-center space-x-2">
                      <ArrowPathIcon className="h-4 w-4 text-amber-600 animate-spin" />
                      <span className="text-sm text-amber-700">Thinking...</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Suggested Questions after response */}
              {!sending && suggestedQuestions.length > 0 && messages.length > 0 && (
                <div className="max-w-4xl">
                  <p className="text-xs font-medium text-gray-600 mb-3">💡 You might also ask:</p>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    {suggestedQuestions.slice(0, 4).map((question, index) => {
                      // Color code buttons based on index
                      const colorClasses = [
                        'bg-amber-50 border-amber-200 hover:bg-amber-100 hover:border-amber-300 text-amber-900',
                        'bg-emerald-50 border-emerald-200 hover:bg-emerald-100 hover:border-emerald-300 text-emerald-900',
                        'bg-blue-50 border-blue-200 hover:bg-blue-100 hover:border-blue-300 text-blue-900',
                        'bg-purple-50 border-purple-200 hover:bg-purple-100 hover:border-purple-300 text-purple-900'
                      ];

                      return (
                        <button
                          key={index}
                          onClick={() => handleSuggestedQuestion(question)}
                          className={`text-left px-4 py-3 rounded-xl text-sm transition-all border hover:-translate-y-0.5 ${colorClasses[index % 4]}`}
                        >
                          {question}
                        </button>
                      );
                    })}
                  </div>
                </div>
              )}

              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Error Message */}
        {error && (
          <div className="px-6 py-3 bg-red-50 border-t border-red-200">
            <p className="text-sm text-red-800">{error}</p>
          </div>
        )}

        {/* Input Area */}
        <div className="px-6 py-4 border-t border-amber-100 bg-amber-50/50">
          <form onSubmit={handleSendMessage} className="flex space-x-3">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask anything - college info, my chances, recommendations..."
              className="flex-1 px-4 py-3 border border-gray-200 rounded-xl focus:ring-amber-500 focus:border-amber-500 bg-white"
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !inputMessage.trim()}
              className={`px-6 py-3 rounded-xl flex items-center space-x-2 transition-all ${sending || !inputMessage.trim()
                ? 'bg-gray-300 cursor-not-allowed'
                : 'bg-gradient-to-r from-amber-500 to-orange-500 hover:from-amber-400 hover:to-orange-400 shadow-lg shadow-amber-200'
                } text-white`}
            >
              {sending ? (
                <>
                  <ArrowPathIcon className="h-5 w-5 animate-spin" />
                  <span>Sending</span>
                </>
              ) : (
                <>
                  <PaperAirplaneIcon className="h-5 w-5" />
                  <span>Send</span>
                </>
              )}
            </button>
          </form>
        </div>
      </div>

      {/* Tips */}
      <div className="bg-white rounded-2xl p-5 border border-gray-100 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-900 mb-3">💡 Tips for better answers:</h3>
        <ul className="text-sm text-gray-600 space-y-2">
          <li className="flex items-start gap-2"><span className="text-amber-500">•</span>Be specific about the college or topic you're asking about</li>
          <li className="flex items-start gap-2"><span className="text-amber-500">•</span>Ask one question at a time for clearer responses</li>
          <li className="flex items-start gap-2"><span className="text-amber-500">•</span>All answers are based on our knowledge base - if information isn't available, we'll let you know</li>
          <li className="flex items-start gap-2"><span className="text-amber-500">•</span>You can ask follow-up questions to dive deeper into any topic</li>
        </ul>
      </div>
    </div>
  );
}

export default Chat;
