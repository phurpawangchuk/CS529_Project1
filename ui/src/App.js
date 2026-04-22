import { useState, useRef, useEffect } from "react";
import ReactMarkdown from "react-markdown";
import "./App.css";

const _BASE = process.env.REACT_APP_API_BASE ?? "http://localhost:8000";

const APIS = {
  "multi-agent": {
    url: _BASE,
    label: "Quiz Mock Master",
    hasSession: true,
  },
  "llm-chat": {
    url: process.env.REACT_APP_LLM_CHAT_BASE ?? "http://localhost:8001",
    label: "LLM Chat (OpenAI)",
    hasSession: false,
  },
};

const REASONING_LEVELS = ["low", "medium", "high"];

const API_BASE = _BASE;

function OTPAuth({ onAuthenticated }) {
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [step, setStep] = useState("email"); // "email" | "otp"
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sentEmail, setSentEmail] = useState("");

  const handleSendOtp = async (e) => {
    e.preventDefault();
    if (!email.trim() || loading) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to send OTP");
      setSentEmail(data.email);
      setStep("otp");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async (e) => {
    e.preventDefault();
    if (!otp.trim() || loading) return;
    setLoading(true);
    setError("");

    try {
      const res = await fetch(`${API_BASE}/auth/verify-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: sentEmail, otp: otp.trim() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Verification failed");
      onAuthenticated(sentEmail);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleResend = async () => {
    setLoading(true);
    setError("");
    setOtp("");
    try {
      const res = await fetch(`${API_BASE}/auth/send-otp`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: sentEmail }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Failed to resend OTP");
      setError("");
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="otp-page">
      <div className="otp-card">
        <div className="otp-brand">
          <span className="otp-brand-icon">{"\u{1F3AF}"}</span>
          <h1>Quiz Mock Master</h1>
        </div>

        {step === "email" ? (
          <>
            <p className="otp-subtitle">Enter your email to receive a one-time password</p>
            <form onSubmit={handleSendOtp} className="otp-form">
              <label>Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="you@example.com"
                required
                autoFocus
              />
              {error && <div className="otp-error">{error}</div>}
              <button type="submit" disabled={loading || !email.trim()}>
                {loading ? "Sending..." : "Send OTP"}
              </button>
            </form>
          </>
        ) : (
          <>
            <p className="otp-subtitle">
              We sent a 6-digit code to <strong>{sentEmail}</strong>
            </p>
            <form onSubmit={handleVerifyOtp} className="otp-form">
              <label>Enter OTP</label>
              <input
                type="text"
                value={otp}
                onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 6))}
                placeholder="------"
                className="otp-code-input"
                maxLength={6}
                required
                autoFocus
              />
              {error && <div className="otp-error">{error}</div>}
              <button type="submit" disabled={loading || otp.length !== 6}>
                {loading ? "Verifying..." : "Verify"}
              </button>
            </form>
            <div className="otp-actions">
              <button className="otp-link-btn" onClick={handleResend} disabled={loading}>
                Resend code
              </button>
              <button className="otp-link-btn" onClick={() => { setStep("email"); setError(""); setOtp(""); }}>
                Change email
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  );
}

function App() {
  const [authenticated, setAuthenticated] = useState(false);
  const [authChecked, setAuthChecked] = useState(false);
  const [userEmail, setUserEmail] = useState("");
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState(null);
  const [loading, setLoading] = useState(false);
  const [activeApi, setActiveApi] = useState("multi-agent");
  const [reasoning, setReasoning] = useState("medium");
  const [totalQuestions, setTotalQuestions] = useState(5);
  const [questionType, setQuestionType] = useState("short_qa");
  const [selectedLesson, setSelectedLesson] = useState(null);
  const [model, setModel] = useState("gpt-4o-mini");
  const [temperature, setTemperature] = useState(0.7);
  const [availableModels, setAvailableModels] = useState(["gpt-4o-mini"]);
  const [lessonConfigs, setLessonConfigs] = useState([]);
  const [quizQuestions, setQuizQuestions] = useState([]);
  const [currentQuestion, setCurrentQuestion] = useState(0);
  const [score, setScore] = useState(0);
  const [quizFinished, setQuizFinished] = useState(false);
  const [quizResults, setQuizResults] = useState([]);
  const [historyData, setHistoryData] = useState(null);
  const [historyLesson, setHistoryLesson] = useState(null);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [historyMenuOpen, setHistoryMenuOpen] = useState(false);
  const [settingsMenuOpen, setSettingsMenuOpen] = useState(false);
  const [uploadPageOpen, setUploadPageOpen] = useState(false);
  const [uploadLesson, setUploadLesson] = useState(1);
  const [uploadDragging, setUploadDragging] = useState(false);
  const [uploadFile, setUploadFile] = useState(null);
  const [uploadStatus, setUploadStatus] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState(null);
  const historyMenuRef = useRef(null);
  const messagesEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const api = APIS[activeApi];
  const isLlm = activeApi === "llm-chat";
  const inQuizMode =
    selectedLesson !== null && quizQuestions.length > 0 && !quizFinished;

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Check if OTP is required (skipped on HF Spaces)
  useEffect(() => {
    fetch(`${API_BASE}/auth/check`)
      .then((res) => res.json())
      .then((data) => {
        if (!data.otp_required) {
          setAuthenticated(true);
          setUserEmail("guest");
        }
        setAuthChecked(true);
      })
      .catch(() => setAuthChecked(true));
  }, []);

  // Fetch settings from backend on mount
  useEffect(() => {
    fetch(`${APIS["multi-agent"].url}/settings/`)
      .then((res) => res.json())
      .then((data) => {
        setModel(data.model || "gpt-4o-mini");
        setTemperature(data.temperature ?? 0.7);
        setAvailableModels(data.available_models || []);
        setLessonConfigs(data.lessons || []);
      })
      .catch(() => {});
  }, []);

  const updateSetting = (updates) => {
    fetch(`${APIS["multi-agent"].url}/settings/`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(updates),
    })
      .then((res) => res.json())
      .then((data) => {
        setModel(data.model);
        setTemperature(data.temperature ?? 0.7);
        setLessonConfigs(data.lessons || []);
      })
      .catch(() => {});
  };

  const handleUpload = async () => {
    if (!uploadFile || uploading) return;
    setUploading(true);
    setUploadStatus(null);

    const formData = new FormData();
    formData.append("file", uploadFile);
    formData.append("lesson_number", uploadLesson);

    try {
      const res = await fetch(`${APIS["multi-agent"].url}/upload/`, {
        method: "POST",
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Upload failed");
      setUploadStatus({ type: "success", message: `Uploaded "${data.filename}" to Lesson ${data.lesson_number}` });
      setUploadFile(null);
      // Refresh settings to update lesson configs
      try {
        const settingsRes = await fetch(`${APIS["multi-agent"].url}/settings/`);
        const settingsData = await settingsRes.json();
        setLessonConfigs(settingsData.lessons || []);
      } catch (e) {
        console.error("Failed to refresh settings after upload:", e);
      }
    } catch (err) {
      setUploadStatus({ type: "error", message: err.message });
    } finally {
      setUploading(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setUploadDragging(false);
    const file = e.dataTransfer.files[0];
    if (file) setUploadFile(file);
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    setUploadDragging(true);
  };

  const handleDragLeave = () => {
    setUploadDragging(false);
  };

  const handleDeleteLesson = async (lessonNumber) => {
    try {
      const res = await fetch(`${APIS["multi-agent"].url}/upload/${lessonNumber}`, {
        method: "DELETE",
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || "Delete failed");
      setDeleteConfirm(null);
      // Refresh lesson configs
      const settingsRes = await fetch(`${APIS["multi-agent"].url}/settings/`);
      const settingsData = await settingsRes.json();
      setLessonConfigs(settingsData.lessons || []);
    } catch (err) {
      alert(`Failed to delete: ${err.message}`);
      setDeleteConfirm(null);
    }
  };

  // Close history menu when clicking outside
  useEffect(() => {
    const handleClickOutside = (e) => {
      if (historyMenuRef.current && !historyMenuRef.current.contains(e.target)) {
        setHistoryMenuOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const generateQuestions = async (lessonNumber) => {
    if (loading) return;
    setUploadPageOpen(false);
    setSelectedLesson(lessonNumber);
    setQuizQuestions([]);
    setCurrentQuestion(0);
    setScore(0);
    setQuizFinished(false);
    setQuizResults([]);
    setMessages([
      {
        role: "user",
        content: `Generate questions for Lesson ${lessonNumber}`,
      },
    ]);
    setLoading(true);

    try {
      const res = await fetch(
        `${APIS["multi-agent"].url}/lessons/${lessonNumber}/generate?question_type=${questionType}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
        }
      );
      const data = await res.json();

      if (!res.ok) {
        const detail = data.detail;
        const errorMsg =
          typeof detail === "object" && detail.message
            ? detail.message
            : detail || "Failed to generate questions";
        throw new Error(errorMsg);
      }

      setQuizQuestions(data.questions);
      setCurrentQuestion(0);

      const questionsText = data.questions
        .map((q, i) => `**Question ${i + 1}:** ${q}`)
        .join("\n\n");

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: `Here are 5 questions for **Lesson ${lessonNumber}**:\n\n${questionsText}\n\n---\n\nLet's start! Please answer **Question 1** below.`,
          agent: "Question Generator",
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          content: `Failed to generate questions: ${err.message}`,
        },
      ]);
      setSelectedLesson(null);
    } finally {
      setLoading(false);
    }
  };

  const submitAnswer = async (e) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const questionNum = currentQuestion + 1;
    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      // Step 1: Assess the answer
      const assessRes = await fetch(
        `${APIS["multi-agent"].url}/lessons/${selectedLesson}/assess`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question_number: questionNum,
            user_answer: text,
          }),
        }
      );
      const assessData = await assessRes.json();

      if (!assessRes.ok) {
        throw new Error(assessData.detail || "Failed to assess answer");
      }

      const isCorrect =
        assessData.grading_result.toUpperCase().includes("CORRECT") &&
        !assessData.grading_result.toUpperCase().includes("INCORRECT");

      if (isCorrect) {
        setScore((prev) => prev + 1);
      }

      // Step 2: Get tutor feedback
      const feedbackRes = await fetch(
        `${APIS["multi-agent"].url}/lessons/${selectedLesson}/feedback`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            question_number: questionNum,
            user_answer: text,
            grading_result: assessData.grading_result,
          }),
        }
      );
      const feedbackData = await feedbackRes.json();

      if (!feedbackRes.ok) {
        throw new Error(feedbackData.detail || "Failed to get feedback");
      }

      const nextQ = currentQuestion + 1;
      const isLast = nextQ >= quizQuestions.length;

      // Collect this question's result
      const thisResult = {
        question_number: questionNum,
        question: quizQuestions[currentQuestion],
        user_answer: text,
        grading_result: assessData.grading_result,
        tutor_feedback: feedbackData.tutor_feedback || "",
      };
      const updatedResults = [...quizResults, thisResult];
      setQuizResults(updatedResults);

      let responseContent = `**${assessData.grading_result}**\n\n${feedbackData.tutor_feedback}`;

      if (isLast) {
        const finalScore = isCorrect ? score + 1 : score;
        responseContent += `\n\n---\n\n**Quiz Complete!** Your score: **${finalScore} / ${quizQuestions.length}**\n\nClick "New Chat" or select another lesson to try again.`;
        setQuizFinished(true);

        // Send quiz results email
        fetch(`${APIS["multi-agent"].url}/lessons/${selectedLesson}/email-results`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            recipient_email: userEmail,
            lesson_number: selectedLesson,
            score: finalScore,
            total: quizQuestions.length,
            results: updatedResults,
          }),
        }).catch(() => {});
      } else {
        responseContent += `\n\n---\n\nPlease answer **Question ${
          nextQ + 1
        }:** ${quizQuestions[nextQ]}`;
        setCurrentQuestion(nextQ);
      }

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: responseContent,
          agent: isLast ? "Quiz Complete" : "Tutor",
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: "error", content: `Error: ${err.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const sendMessage = async (e) => {
    // If in quiz mode, route to quiz answer handler
    if (inQuizMode) {
      return submitAnswer(e);
    }

    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const body = { message: text };

      if (api.hasSession && sessionId) {
        body.session_id = sessionId;
      }

      // LLM Chat supports extra options
      if (isLlm) {
        body.reasoning = reasoning;
      }

      const res = await fetch(`${api.url}/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      const data = await res.json();

      if (data.session_id) setSessionId(data.session_id);

      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: data.reply,
          agent: data.agent || null,
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          content: `Failed to reach ${api.label}. Is the API running?`,
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const resetChat = async () => {
    if (api.hasSession && sessionId) {
      await fetch(`${api.url}/reset?session_id=${sessionId}`, {
        method: "POST",
      }).catch(() => {});
    }
    setMessages([]);
    setSessionId(null);
    setSelectedLesson(null);
    setQuizQuestions([]);
    setCurrentQuestion(0);
    setScore(0);
    setQuizFinished(false);
    setQuizResults([]);
    setHistoryData(null);
    setHistoryLesson(null);
    setUploadPageOpen(false);
  };

  const fetchHistory = async (lessonNumber) => {
    if (historyLoading) return;
    setHistoryMenuOpen(false);
    setHistoryLoading(true);
    setHistoryLesson(lessonNumber);
    setHistoryData(null);
    setUploadPageOpen(false);
    // Clear quiz state when viewing history
    setMessages([]);
    setSelectedLesson(null);
    setQuizQuestions([]);
    setCurrentQuestion(0);
    setScore(0);
    setQuizFinished(false);
    setQuizResults([]);

    try {
      const res = await fetch(
        `${APIS["multi-agent"].url}/lessons/${lessonNumber}/history`
      );
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || "Failed to fetch history");
      }
      setHistoryData(data);
    } catch (err) {
      setHistoryData({ error: err.message });
    } finally {
      setHistoryLoading(false);
    }
  };

  const welcomeText = isLlm
    ? "Ask anything — powered by OpenAI's Responses API. Use the controls below to set reasoning effort, instructions, or translation."
    : "An interactive chatbot that tests student understanding across 5 lesson documents. Each lesson generates 5 questions from the uploaded material and evaluates the student's answers with grading and tutor feedback.";

  const placeholderText = inQuizMode
    ? `Answer Question ${currentQuestion + 1}...`
    : "Type your message...";

  if (!authChecked) {
    return null; // Wait for auth check
  }

  if (!authenticated) {
    return (
      <OTPAuth
        onAuthenticated={(email) => {
          setUserEmail(email);
          setAuthenticated(true);
        }}
      />
    );
  }

  return (
    <div className="app-layout">
      {/* Sidebar */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <span className="sidebar-brand-icon">{"\u{1F3AF}"}</span>
          Quiz Mock Master
        </div>
        <nav className="sidebar-nav">
          {/* History */}
          <div className="sidebar-menu-item" ref={historyMenuRef}>
            <button
              className={`sidebar-menu-btn ${historyMenuOpen ? "open" : ""}`}
              onClick={() => setHistoryMenuOpen((prev) => !prev)}>
              <span className="sidebar-icon">&#128218;</span>
              <span>History</span>
              <span className={`sidebar-chevron ${historyMenuOpen ? "open" : ""}`}>&#8249;</span>
            </button>
            {historyMenuOpen && (
              <div className="sidebar-submenu">
                {lessonConfigs.filter((lc) => lc.configured).map((lc) => (
                  <button
                    key={lc.lesson_number}
                    className={`sidebar-submenu-item ${historyLesson === lc.lesson_number ? "active" : ""}`}
                    onClick={() => fetchHistory(lc.lesson_number)}
                    disabled={historyLoading}>
                    <span className="sidebar-icon">&#128209;</span>
                    Lesson {lc.lesson_number}
                  </button>
                ))}
              </div>
            )}
          </div>

          {/* Settings */}
          <div className="sidebar-menu-item">
            <button
              className={`sidebar-menu-btn ${settingsMenuOpen ? "open" : ""}`}
              onClick={() => setSettingsMenuOpen((prev) => !prev)}>
              <span className="sidebar-icon">&#9881;</span>
              <span>Settings</span>
              <span className={`sidebar-chevron ${settingsMenuOpen ? "open" : ""}`}>&#8249;</span>
            </button>
            {settingsMenuOpen && (
              <div className="sidebar-submenu">
                <div className="sidebar-settings-group">
                  <label>Lesson Configuration</label>
                  <div className="sidebar-lesson-configs">
                    {lessonConfigs.map((lc) => (
                      <div key={lc.lesson_number} className="sidebar-lesson-config-item">
                        <span>Lesson {lc.lesson_number}</span>
                        <span className={`sidebar-config-status ${lc.configured ? "configured" : "not-configured"}`}>
                          {lc.configured ? "Configured" : "Not configured"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="sidebar-settings-group">
                  <label>Model</label>
                  <select
                    value={model}
                    onChange={(e) => {
                      setModel(e.target.value);
                      updateSetting({ model: e.target.value });
                    }}>
                    {(availableModels.length > 0 ? availableModels : ["gpt-4o-mini", "gpt-4o", "gpt-4.1", "gpt-4.1-mini", "gpt-4.1-nano"]).map((m) => (
                      <option key={m} value={m}>{m}</option>
                    ))}
                  </select>
                </div>
                <div className="sidebar-settings-group">
                  <label>Temperature: {temperature.toFixed(1)}</label>
                  <input
                    type="range"
                    min="0"
                    max="1"
                    step="0.1"
                    value={temperature}
                    onChange={(e) => {
                      setTemperature(parseFloat(e.target.value));
                    }}
                  />
                  <div className="sidebar-range-labels">
                    <span>Precise</span>
                    <span>Creative</span>
                  </div>
                </div>
                <div className="sidebar-settings-group">
                  <label>Total Questions</label>
                  <select
                    className="sidebar-select"
                    value={totalQuestions}
                    onChange={(e) => setTotalQuestions(parseInt(e.target.value))}
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </div>
                <div className="sidebar-settings-group">
                  <label>Question Type</label>
                  <select
                    className="sidebar-select"
                    value={questionType}
                    onChange={(e) => setQuestionType(e.target.value)}
                  >
                    <option value="short_qa">Short Q/A</option>
                    <option value="mcq">MCQ</option>
                    <option value="fill_blank">Fill the Blank</option>
                    <option value="mixed">Mixed</option>
                  </select>
                </div>
                <div className="sidebar-settings-group">
                  <button
                    className="sidebar-apply-btn"
                    onClick={() => {
                      updateSetting({
                        model,
                        questions_per_lesson: totalQuestions,
                      });
                      setSettingsMenuOpen(false);
                    }}
                  >
                    Apply
                  </button>
                </div>
                <div className="sidebar-settings-group">
                  <label>Reasoning</label>
                  <div className="sidebar-reasoning-buttons">
                    {REASONING_LEVELS.map((level) => (
                      <button
                        key={level}
                        className={`sidebar-reason-btn ${reasoning === level ? "active" : ""}`}
                        onClick={() => setReasoning(level)}>
                        {level}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>

          {/* Upload */}
          <button
            className={`sidebar-menu-btn ${uploadPageOpen ? "open" : ""}`}
            onClick={() => {
              setUploadPageOpen(true);
              setMessages([]);
              setHistoryData(null);
              setHistoryLesson(null);
              setSelectedLesson(null);
              setQuizQuestions([]);
              setQuizFinished(false);
    setQuizResults([]);
            }}>
            <span className="sidebar-icon">{"\u{1F4E4}"}</span>
            <span>Upload</span>
          </button>

          {/* Logout */}
          <button
            className="sidebar-menu-btn sidebar-logout-btn"
            onClick={() => {
              setAuthenticated(false);
              setUserEmail("");
              resetChat();
            }}>
            <span className="sidebar-icon">{"\u{1F6AA}"}</span>
            <span>Logout</span>
          </button>
        </nav>
      </aside>

      <div className="chat-container">
        <header className="chat-header">
          <span className="header-user">Welcome, {userEmail.split("@")[0].replace(/\d+$/g, "").replace(/[._]/g, " ").replace(/\b\w/g, c => c.toUpperCase()).trim() || userEmail.split("@")[0]} ({userEmail})</span>
          <div className="header-spacer" />
          <button className="reset-btn" onClick={resetChat}>
            New Chat
          </button>
        </header>

      {/* Quiz progress bar */}
      {inQuizMode && (
        <div className="quiz-progress">
          <span>
            Lesson {selectedLesson} — Question {currentQuestion + 1} of{" "}
            {quizQuestions.length}
          </span>
          <span>Score: {score}</span>
        </div>
      )}

      <div className="chat-messages">
        {uploadPageOpen && (
          <div className="upload-page">
            <div className="upload-page-header">
              <h2>Upload Lesson Documents</h2>
              <p>Upload PDF, TXT, or DOCX files to configure lessons for quiz generation.</p>
            </div>

            <div className="upload-page-form">
              <div className="upload-page-field">
                <label>Select Lesson</label>
                <select
                  value={uploadLesson}
                  onChange={(e) => setUploadLesson(Number(e.target.value))}>
                  {Array.from({ length: 5 }, (_, i) => i + 1).map((n) => (
                    <option key={n} value={n}>Lesson {n}</option>
                  ))}
                </select>
              </div>

              <div
                className={`upload-dropzone-large ${uploadDragging ? "dragging" : ""}`}
                onDrop={handleDrop}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onClick={() => fileInputRef.current?.click()}>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt,.docx"
                  style={{ display: "none" }}
                  onChange={(e) => {
                    if (e.target.files[0]) setUploadFile(e.target.files[0]);
                  }}
                />
                {uploadFile ? (
                  <div className="upload-file-selected">
                    <span className="upload-file-icon-lg">{"\u{1F4C4}"}</span>
                    <div>
                      <div className="upload-file-name-lg">{uploadFile.name}</div>
                      <div className="upload-file-size">{(uploadFile.size / 1024).toFixed(1)} KB</div>
                    </div>
                    <button
                      className="upload-file-remove"
                      onClick={(e) => { e.stopPropagation(); setUploadFile(null); }}>
                      &#10005;
                    </button>
                  </div>
                ) : (
                  <div className="upload-placeholder-large">
                    <span className="upload-drop-icon-lg">{"\u{1F4C1}"}</span>
                    <span className="upload-drop-text">Drag & drop your file here</span>
                    <span className="upload-drop-or">or</span>
                    <span className="upload-browse-link">Browse files</span>
                    <span className="upload-hint-lg">Supported: PDF, TXT, DOCX</span>
                  </div>
                )}
              </div>

              {uploadStatus && (
                <div className={`upload-status-lg ${uploadStatus.type}`}>
                  {uploadStatus.type === "success" ? "\u2705" : "\u274C"} {uploadStatus.message}
                </div>
              )}

              <button
                className="upload-submit-btn-lg"
                onClick={handleUpload}
                disabled={!uploadFile || uploading}>
                {uploading ? "Uploading..." : "Upload Document"}
              </button>
            </div>

            <div className="upload-page-table">
              <h3>Uploaded Documents</h3>
              <table>
                <thead>
                  <tr>
                    <th>Lesson</th>
                    <th>Filename</th>
                    <th>Status</th>
                    <th>Vector Store ID</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {lessonConfigs.filter((lc) => lc.configured).length > 0 ? (
                    lessonConfigs
                      .filter((lc) => lc.configured)
                      .map((lc) => (
                        <tr key={lc.lesson_number}>
                          <td>Lesson {lc.lesson_number}</td>
                          <td>{lc.filename || "—"}</td>
                          <td>
                            <span className="upload-table-status configured">Available</span>
                          </td>
                          <td className="upload-table-vsid">{lc.vector_store_id}</td>
                          <td>
                            <button
                              className="upload-delete-btn"
                              onClick={() => setDeleteConfirm(lc.lesson_number)}>
                              Delete
                            </button>
                          </td>
                        </tr>
                      ))
                  ) : (
                    <tr>
                      <td colSpan="5" className="upload-table-empty">No documents uploaded yet.</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {messages.length === 0 && !historyData && !uploadPageOpen && (
          <div className="welcome">
            <h2>Welcome, {userEmail.split("@")[0].replace(/\d+$/g, "").replace(/[._]/g, " ").replace(/\b\w/g, c => c.toUpperCase()).trim() || userEmail.split("@")[0]}!</h2>
            <p>{welcomeText}</p>
            {!isLlm && (
              <div className="lesson-buttons">
                {lessonConfigs.filter((lc) => lc.configured).length > 0 ? (
                  lessonConfigs.filter((lc) => lc.configured).map((lc) => (
                    <button
                      key={lc.lesson_number}
                      className="lesson-btn"
                      onClick={() => generateQuestions(lc.lesson_number)}
                      disabled={loading}>
                      Lesson {lc.lesson_number}
                    </button>
                  ))
                ) : (
                  <p className="no-lessons-hint">No lessons uploaded yet. Use the Upload page to add lesson documents.</p>
                )}
              </div>
            )}
          </div>
        )}
        {historyData && historyLesson && (
          <div className="history-view">
            <div className="history-header">
              <h3>Lesson {historyLesson} — Quiz History</h3>
            </div>
            {historyData.error ? (
              <p className="history-error">{historyData.error}</p>
            ) : historyData.assessments && historyData.assessments.length > 0 ? (
              historyData.assessments.map((a, i) => {
                const fb = historyData.feedback?.find(
                  (f) => f.question_number === a.question_number && f.created_at?.slice(0, 16) === a.created_at?.slice(0, 16)
                ) || historyData.feedback?.[i];
                const isCorrect =
                  a.grading_result.toUpperCase().includes("CORRECT") &&
                  !a.grading_result.toUpperCase().includes("INCORRECT");
                return (
                  <div key={i} className={`history-card ${isCorrect ? "card-correct" : "card-incorrect"}`}>
                    <div className="history-q-header">
                      <span className="history-q-num">Q{a.question_number}</span>
                      <span className={`history-verdict ${isCorrect ? "correct" : "incorrect"}`}>
                        {isCorrect ? "Correct" : "Incorrect"}
                      </span>
                      <span className="history-date">
                        {new Date(a.created_at).toLocaleDateString("en-US", { year: "numeric", month: "long", day: "numeric" })}
                      </span>
                    </div>
                    {a.question && (
                      <div className="history-question">
                        <strong>Question:</strong> {a.question}
                      </div>
                    )}
                    <div className="history-answer">
                      <strong>Your answer:</strong> {a.user_answer}
                    </div>
                    <div className="history-grading">
                      <ReactMarkdown>{a.grading_result}</ReactMarkdown>
                    </div>
                    {fb && (
                      <div className="history-feedback">
                        <strong>Tutor Feedback:</strong>
                        <ReactMarkdown>{fb.tutor_feedback}</ReactMarkdown>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <p className="history-empty">No quiz attempts yet for Lesson {historyLesson}.</p>
            )}
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`message ${msg.role}`}>
            {msg.agent && <span className="agent-badge">{msg.agent}</span>}
            <div className="message-content">
              {msg.role === "assistant" ? (
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        {loading && (
          <div className="message assistant">
            <div className="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </div>
          </div>
        )}
        <div ref={messagesEndRef} />
      </div>

      <form className="chat-input" onSubmit={sendMessage}>
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder={placeholderText}
          disabled={loading}
          autoFocus
        />
        <button type="submit" disabled={loading || !input.trim()}>
          Send
        </button>
      </form>
    </div>

      {/* Delete Confirmation Modal */}
      {deleteConfirm !== null && (
        <div className="modal-overlay" onClick={() => setDeleteConfirm(null)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h3>Delete Lesson {deleteConfirm}</h3>
            <p>Are you sure you want to delete this document? This will also remove it from OpenAI storage.</p>
            <div className="modal-actions">
              <button className="modal-cancel-btn" onClick={() => setDeleteConfirm(null)}>
                Cancel
              </button>
              <button className="modal-delete-btn" onClick={() => handleDeleteLesson(deleteConfirm)}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
