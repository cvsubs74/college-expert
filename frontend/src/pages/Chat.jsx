import { useState, useEffect, useRef } from 'react';
import {
  ChatBubbleLeftRightIcon,
  PaperAirplaneIcon,
  ArrowPathIcon,
  InformationCircleIcon,
  SparklesIcon
} from '@heroicons/react/24/outline';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { startSession, sendMessage, extractFullResponse } from '../services/api';
import { useAuth } from '../context/AuthContext';

function Chat() {
  const { currentUser } = useAuth();
  const [messages, setMessages] = useState([]);
  const [inputMessage, setInputMessage] = useState('');
  const [sending, setSending] = useState(false);
  const [error, setError] = useState(null);
  const [suggestedQuestions, setSuggestedQuestions] = useState([]);
  const messagesEndRef = useRef(null);

  // Load messages from localStorage
  useEffect(() => {
    const savedMessages = localStorage.getItem('chatMessages');
    
    if (savedMessages) {
      try {
        setMessages(JSON.parse(savedMessages));
      } catch (e) {
        console.error('Error loading messages:', e);
      }
    }
  }, []);

  // Save messages to localStorage
  useEffect(() => {
    if (messages.length > 0) localStorage.setItem('chatMessages', JSON.stringify(messages));
  }, [messages]);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Clear messages when user signs out
  useEffect(() => {
    if (!currentUser) {
      setMessages([]);
      setError(null);
    }
  }, [currentUser]);

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    if (!inputMessage.trim() || sending) return;

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

      // Use startSession - it will reuse existing session or create new one
      const response = await startSession(knowledgeBaseQuery, currentUser?.email);

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

  const handleNewChat = () => {
    setMessages([]);
    setError(null);
    setSuggestedQuestions([]);
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

      // Use startSession - it will reuse existing session or create new one
      const response = await startSession(knowledgeBaseQuery, currentUser?.email);

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

  // Generic suggested questions for initial load
  const defaultSuggestedQuestions = [
    "How do colleges evaluate applications holistically?",
    "What role do standardized test scores play in admissions?",
    "How important are extracurricular activities in college applications?",
    "What makes a strong college application essay?"
  ];

  // Display suggested questions - use dynamic ones if available, otherwise defaults
  const displayedQuestions = suggestedQuestions.length > 0 ? suggestedQuestions : defaultSuggestedQuestions;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">College Information Chat</h1>
        <p className="mt-2 text-gray-600">
          Ask questions about colleges, admissions requirements, and application strategies. 
          All answers are based on our curated knowledge base.
        </p>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
        <div className="flex">
          <InformationCircleIcon className="h-5 w-5 text-blue-600 flex-shrink-0 mt-0.5" />
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-900">Knowledge Base Powered</h3>
            <p className="mt-1 text-sm text-blue-800">
              This chat uses our college admissions knowledge base to provide accurate, 
              research-backed answers. Responses are grounded in expert insights and official data.
            </p>
          </div>
        </div>
      </div>

      {/* Chat Container */}
      <div className="bg-white shadow rounded-lg flex flex-col" style={{ height: '600px' }}>
        {/* Chat Header */}
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <div className="flex items-center">
            <ChatBubbleLeftRightIcon className="h-6 w-6 text-primary mr-2" />
            <h2 className="text-lg font-semibold text-gray-900">Ask About Colleges</h2>
          </div>
          {messages.length > 0 && (
            <button
              onClick={handleNewChat}
              className="text-sm text-gray-600 hover:text-primary transition-colors"
            >
              New Chat
            </button>
          )}
        </div>

        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 ? (
            <div className="text-center py-12">
              <SparklesIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
              <h3 className="text-lg font-medium text-gray-900 mb-2">Start a Conversation</h3>
              <p className="text-gray-600 mb-6">Ask any question about college admissions</p>
              
              {/* Suggested Questions */}
              <div className="max-w-2xl mx-auto">
                <p className="text-sm font-medium text-gray-700 mb-3">💡 Suggested questions:</p>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {displayedQuestions.map((question, index) => {
                    // Color code buttons based on index
                    const colorClasses = [
                      'bg-blue-50 border-blue-300 hover:bg-blue-100 hover:border-blue-400 text-blue-900',
                      'bg-green-50 border-green-300 hover:bg-green-100 hover:border-green-400 text-green-900',
                      'bg-purple-50 border-purple-300 hover:bg-purple-100 hover:border-purple-400 text-purple-900',
                      'bg-orange-50 border-orange-300 hover:bg-orange-100 hover:border-orange-400 text-orange-900'
                    ];
                    
                    return (
                      <button
                        key={index}
                        onClick={() => handleSuggestedQuestion(question)}
                        className={`text-left px-4 py-3 rounded-lg text-sm transition-colors border ${colorClasses[index % 4]}`}
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
                    className={`max-w-3xl rounded-lg px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-primary text-white'
                        : 'bg-gray-100 text-gray-900'
                    }`}
                  >
                    {message.role === 'user' ? (
                      <p className="text-sm">{message.content}</p>
                    ) : (
                      <div className="prose prose-sm max-w-none prose-blue">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {message.content}
                        </ReactMarkdown>
                      </div>
                    )}
                  </div>
                </div>
              ))}
              
              {sending && (
                <div className="flex justify-start">
                  <div className="bg-gray-100 rounded-lg px-4 py-3">
                    <div className="flex items-center space-x-2">
                      <ArrowPathIcon className="h-4 w-4 text-gray-600 animate-spin" />
                      <span className="text-sm text-gray-600">Thinking...</span>
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
                        'bg-blue-50 border-blue-300 hover:bg-blue-100 hover:border-blue-400 text-blue-900',
                        'bg-green-50 border-green-300 hover:bg-green-100 hover:border-green-400 text-green-900',
                        'bg-purple-50 border-purple-300 hover:bg-purple-100 hover:border-purple-400 text-purple-900',
                        'bg-orange-50 border-orange-300 hover:bg-orange-100 hover:border-orange-400 text-orange-900'
                      ];
                      
                      return (
                        <button
                          key={index}
                          onClick={() => handleSuggestedQuestion(question)}
                          className={`text-left px-4 py-3 rounded-lg text-sm transition-colors border ${colorClasses[index % 4]}`}
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
        <div className="px-6 py-4 border-t border-gray-200">
          <form onSubmit={handleSendMessage} className="flex space-x-3">
            <input
              type="text"
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              placeholder="Ask about colleges, admissions, or application strategies..."
              className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-primary focus:border-primary"
              disabled={sending}
            />
            <button
              type="submit"
              disabled={sending || !inputMessage.trim()}
              className={`px-6 py-3 rounded-lg flex items-center space-x-2 ${
                sending || !inputMessage.trim()
                  ? 'bg-gray-400 cursor-not-allowed'
                  : 'bg-primary hover:bg-blue-700'
              } text-white transition-colors`}
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
      <div className="bg-gray-50 rounded-lg p-4">
        <h3 className="text-sm font-medium text-gray-900 mb-2">Tips for better answers:</h3>
        <ul className="text-sm text-gray-700 space-y-1 list-disc list-inside">
          <li>Be specific about the college or topic you're asking about</li>
          <li>Ask one question at a time for clearer responses</li>
          <li>All answers are based on our knowledge base - if information isn't available, we'll let you know</li>
          <li>You can ask follow-up questions to dive deeper into any topic</li>
        </ul>
      </div>
    </div>
  );
}

export default Chat;
