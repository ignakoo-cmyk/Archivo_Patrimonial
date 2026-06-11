"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Search, ExternalLink, Landmark, User, Loader2, BookOpen, Library, MessageCircle, X, ChevronRight, FileText, Clock, Sparkles } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

// Interfaces actualizadas para coincidir con el contrato definido en types/archive.ts
interface RichCard {
  id: string;
  titulo: string;
  codigo_referencia: string;
  anio: string | null;
  url: string;
  descripcion_corta: string;
  materias: string[];
  miniatura_url: string | null;
  relevancia: number;
}

interface QuickReply {
  label: string;
  value: string;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  documents?: any[];
  rich_cards?: RichCard[];
  quick_replies?: QuickReply[];
  isLoading?: boolean;
}

const Avatar = ({ role }: { role: "user" | "assistant" }) => {
  if (role === "user") {
    return (
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500">
        <User size={16} />
      </div>
    );
  }
  return (
    <div className="flex-shrink-0 w-8 h-8 rounded-full bg-[#003366] flex items-center justify-center text-white text-[10px] font-bold tracking-widest">
      UAH
    </div>
  );
};

export default function ArchivePage() {
  const [isChatOpen, setIsChatOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "¡Hola! Soy el asistente del **Archivo Patrimonial UAH**.\n\nPuedo ayudarte a buscar documentos históricos, colecciones fotográficas, fondos documentales y más. ¿Qué te gustaría encontrar?",
    },
  ]);
  const [input, setInput] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const chatInputRef = useRef<HTMLInputElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (isChatOpen && chatInputRef.current) {
      setTimeout(() => chatInputRef.current?.focus(), 300);
    }
  }, [isChatOpen]);

  const sendMessage = async (query: string) => {
    if (!query.trim() || isTyping) return;

    console.log("Iniciando búsqueda para:", query);
    
    // Abrir el chat inmediatamente para feedback visual
    setIsChatOpen(true);

    const userMessage: Message = { id: Date.now().toString(), role: "user", content: query };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setSearchInput("");
    setIsTyping(true);

    const loadingId = "loading-" + Date.now();
    setMessages((prev) => [...prev, { id: loadingId, role: "assistant", content: "", isLoading: true }]);

    try {
      // Intentar obtener URL de variable de entorno o usar localhost:3000 por defecto
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:3000`;
      console.log("Conectando a API en:", apiUrl);

      const res = await fetch(`${apiUrl}/api/v1/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query }),
      });

      if (!res.ok) throw new Error(`HTTP Error: ${res.status}`);
      
      const data = await res.json();
      console.log("Respuesta recibida:", data);

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingId
            ? { 
                id: Date.now().toString(), 
                role: "assistant", 
                content: data.response || "No recibí una respuesta clara del asistente.",
                documents: data.documents,
                rich_cards: data.rich_cards, // Soporte para la nueva arquitectura
                quick_replies: data.quick_replies // Soporte para la nueva arquitectura
              }
            : msg
        )
      );
    } catch (error) {
      console.log("Error en la búsqueda:", error);
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingId
            ? { id: Date.now().toString(), role: "assistant", content: "Error de conexión: No se pudo contactar con el asistente. Por favor, asegúrate de que el backend esté corriendo correctamente." }
            : msg
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  const handleMainSearch = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchInput.trim()) {
      sendMessage(searchInput);
    }
  };

  const handleChatSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      sendMessage(input);
    }
  };

  return (
    <div className="page-layout">
      {/* ═══════════════ MAIN CONTENT AREA ═══════════════ */}
      <div className={`main-content ${isChatOpen ? "chat-open" : ""}`}>
        {/* CABECERA */}
        <header className="uah-header">
          <div className="uah-header-inner">
            <div className="uah-logo-group">
              <div className="uah-logo-circle">
                <span>UAH</span>
              </div>
              <div className="uah-logo-text">
                <span className="uah-logo-title">Universidad Alberto Hurtado</span>
                <span className="uah-logo-subtitle">Archivo Patrimonial</span>
              </div>
            </div>
            <nav className="uah-nav">
              <a href="https://archivopatrimonial.uahurtado.cl/" target="_blank">Quienes Somos</a>
              <a href="https://archivopatrimonial.uahurtado.cl/" target="_blank">Sitios de Interés</a>
              <a href="https://archivopatrimonial.uahurtado.cl/" target="_blank">Fondos</a>
              <button className="uah-nav-login">Iniciar Sesión</button>
            </nav>
          </div>
        </header>

        {/* HERO */}
        <section className="hero-section">
          <div className="hero-inner">
            <h1 className="hero-title">
              Explora el <span className="hero-accent">Archivo Patrimonial</span>
            </h1>
            <p className="hero-subtitle">
              Accede a colecciones históricas, fondos documentales y recursos preservados por la Universidad Alberto Hurtado.
            </p>

            <form onSubmit={handleMainSearch} className="hero-search-form">
              <div className="hero-search-icon">
                <Search size={22} />
              </div>
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                placeholder="Buscar en el archivo patrimonial..."
                className="hero-search-input"
              />
              <button type="submit" disabled={!searchInput.trim() || isTyping} className="hero-search-btn">
                {isTyping ? <Loader2 size={20} className="animate-spin" /> : "Buscar"}
              </button>
            </form>

            <div className="hero-categories">
              <div className="hero-category-item" onClick={() => sendMessage("Mostrar materias")}>
                <div className="hero-category-icon"><BookOpen size={26} /></div>
                <span>Materias</span>
              </div>
              <div className="hero-category-item" onClick={() => sendMessage("Mostrar fondos")}>
                <div className="hero-category-icon"><Library size={26} /></div>
                <span>Fondos</span>
              </div>
              <div className="hero-category-item" onClick={() => sendMessage("Mostrar documentos")}>
                <div className="hero-category-icon"><FileText size={26} /></div>
                <span>Documentos</span>
              </div>
              <div className="hero-category-item" onClick={() => sendMessage("Mostrar documentos recientes")}>
                <div className="hero-category-icon"><Clock size={26} /></div>
                <span>Recientes</span>
              </div>
            </div>
          </div>
        </section>

        {/* INFO CARDS */}
        <section className="info-section">
          <div className="info-grid">
            <div className="info-card">
              <div className="info-card-icon"><BookOpen size={32} /></div>
              <h3>12.400+ Documentos</h3>
              <p>Accede a miles de registros históricos indexados y catalogados.</p>
            </div>
            <div className="info-card">
              <div className="info-card-icon"><Sparkles size={32} /></div>
              <h3>Búsqueda con IA</h3>
              <p>Nuestro asistente inteligente entiende tus preguntas en lenguaje natural.</p>
            </div>
            <div className="info-card">
              <div className="info-card-icon"><FileText size={32} /></div>
              <h3>Fondos Patrimoniales</h3>
              <p>Colecciones fotográficas, documentales y audiovisuales de la UAH.</p>
            </div>
          </div>
        </section>

        {/* FOOTER */}
        <footer className="uah-footer">
          <div className="uah-footer-grid">
            <div>
              <h3 className="footer-title">UAH / Universidad Alberto Hurtado</h3>
              <p>Av. Bernardo O&apos;Higgins 1825</p>
              <p>Santiago de Chile</p>
            </div>
            <div>
              <h4 className="footer-heading">Sitios de Interés</h4>
              <ul>
                <li><a href="#">Ciencias Sociales</a></li>
                <li><a href="#">Derecho</a></li>
                <li><a href="#">Economía y Negocios</a></li>
              </ul>
            </div>
            <div>
              <h4 className="footer-heading">Contacto</h4>
              <p>Teléfono: +56 2 2692 0200</p>
              <p className="footer-email">archivo@uahurtado.cl</p>
            </div>
          </div>
        </footer>
      </div>

      {/* ═══════════════ CHAT SIDEBAR (RIGHT) ═══════════════ */}
      <aside className={`chat-sidebar ${isChatOpen ? "open" : "closed"}`}>
        {/* Chat Header */}
        <div className="chat-header">
          <div className="chat-header-left">
            <div className="chat-avatar !bg-[#003366]">
              <span className="text-white text-[11px] font-bold tracking-widest">UAH</span>
            </div>
            <div>
              <h3 className="chat-title">Asistente IA</h3>
              <p className="chat-subtitle">Archivo Patrimonial UAH</p>
            </div>
          </div>
          <button onClick={() => setIsChatOpen(false)} className="chat-close-btn" aria-label="Cerrar chat">
            <X size={18} />
          </button>
        </div>

        {/* Chat Messages */}
        <div className="chat-messages">
          {messages.map((msg) => (
            <div key={msg.id} className={`chat-msg ${msg.role}`}>
              {msg.role === "user" ? (
                <div className="flex items-start gap-2 flex-row-reverse w-full">
                  <Avatar role="user" />
                  <div className="chat-bubble-user !bg-gray-100 !text-gray-800 !border !border-gray-200 !shadow-sm">{msg.content}</div>
                </div>
              ) : (
                <div className="flex items-start gap-2 w-full">
                  <Avatar role="assistant" />
                  <div className="chat-bubble-ai !bg-white !border !border-gray-200 !shadow-sm">
                  {msg.isLoading ? (
                    <div className="chat-loading">
                      <div className="chat-loading-dots">
                        <span></span><span></span><span></span>
                      </div>
                      <span className="chat-loading-text">Consultando archivo...</span>
                    </div>
                  ) : (
                    <div className="chat-prose">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                    </div>
                  )}

                  {/* RENDERIZADO DE RICH CARDS (Arquitectura Hexagonal) */}
                  {msg.rich_cards && msg.rich_cards.length > 0 && (
                    <div className="chat-rich-cards">
                      <div className="chat-docs-header">
                        <Sparkles size={12} />
                        <span>Documentos Encontrados ({msg.rich_cards.length})</span>
                      </div>
                      <div className="rich-cards-grid">
                        {msg.rich_cards.map((card) => (
                          <div key={card.id} className="rich-card">
                            {card.miniatura_url && (
                              <div className="rich-card-img">
                                <img src={card.miniatura_url} alt={card.titulo} />
                              </div>
                            )}
                            <div className="rich-card-body">
                              <span className="rich-card-code">{card.codigo_referencia}</span>
                              <h4 className="rich-card-title">{card.titulo}</h4>
                              <p className="rich-card-desc">{card.descripcion_corta}</p>
                              <div className="rich-card-footer">
                                <span className="rich-card-relevance">{Math.round((card.relevancia || 0) * 100)}%</span>
                                <a href={card.url} target="_blank" rel="noopener noreferrer" className="rich-card-link">
                                  Ver Ficha <ExternalLink size={12} />
                                </a>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  {/* FALLBACK PARA DOCUMENTOS SIMPLES */}
                  {!msg.rich_cards && msg.documents && msg.documents.length > 0 && (
                    <div className="chat-docs">
                      <div className="chat-docs-header">
                        <FileText size={12} />
                        <span>Fuentes ({msg.documents.length})</span>
                      </div>
                      {msg.documents.slice(0, 3).map((doc, idx) => (
                        <a key={idx} href={doc.href} target="_blank" rel="noopener noreferrer" className="chat-doc-card">
                          <div className="chat-doc-title">{doc.title}</div>
                          <div className="chat-doc-meta">
                            <span className="chat-doc-score">
                              {((doc.relevance_score || 0) * 100).toFixed(0)}% relevancia
                            </span>
                            <ChevronRight size={12} />
                          </div>
                        </a>
                      ))}
                    </div>
                  )}
                  
                  {/* QUICK REPLIES */}
                  {msg.quick_replies && msg.quick_replies.length > 0 && (
                    <div className="chat-quick-replies">
                      {msg.quick_replies.map((reply, idx) => (
                        <button 
                          key={idx} 
                          onClick={() => sendMessage(reply.value)}
                          className="quick-reply-btn"
                        >
                          {reply.label}
                        </button>
                      ))}
                    </div>
                  )}
                  </div>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} className="chat-scroll-anchor" />
        </div>

        {/* Chat Input */}
        <div className="chat-input-area">
          <form onSubmit={handleChatSubmit} className="chat-input-form">
            <input
              ref={chatInputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pregunta sobre el archivo..."
              className="chat-input"
              disabled={isTyping}
            />
            <button type="submit" disabled={!input.trim() || isTyping} className="chat-send-btn" aria-label="Enviar">
              <Send size={16} />
            </button>
          </form>
          <div className="chat-powered">Powered by Gemini AI · Arquitectura Hexagonal</div>
        </div>
      </aside>

      {/* ═══════════════ FLOATING OPEN BUTTON ═══════════════ */}
      {!isChatOpen && (
        <button onClick={() => setIsChatOpen(true)} className="chat-fab" aria-label="Abrir chat del Archivo">
          <MessageCircle size={26} />
          <span className="chat-fab-label">Asistente IA</span>
        </button>
      )}
    </div>
  );
}
