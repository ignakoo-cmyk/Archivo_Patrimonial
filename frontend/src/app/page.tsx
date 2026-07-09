"use client";

import { useState, useRef, useEffect } from "react";
import { Loader2, Send, Bot, Sparkles, FileText, ChevronRight, ExternalLink, Search, Landmark, User, BookOpen, Library, MessageCircle, X, Clock, AlertCircle, WifiOff } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import QuickExplorationMenu, { ExplorationData } from "../components/QuickExplorationMenu";

const exploreData: ExplorationData = {
  materias: [
    { name: "Derechos Humanos", count: 87 },
    { name: "Dictadura (Chile)", count: 42 },
    { name: "Educación (Chile)", count: 53 },
    { name: "Economía", count: 148 },
    { name: "Leyes (Chile)", count: 35 },
    { name: "Prensa", count: 63 },
    { name: "Plebiscito (Chile)", count: 59 },
    { name: "Partidos políticos (Chile)", count: 34 },
    { name: "Detenidos desaparecidos", count: 14 }
  ],
  personajes: [
    { name: "Aylwin Azócar, Patricio", count: 307 },
    { name: "Correa Opazo, Pedro", count: 227 },
    { name: "Foxley, Alejandro", count: 133 },
    { name: "Bascuñán Edwards, Carlos", count: 126 },
    { name: "Lagos Escobar, Ricardo", count: 48 }
  ],
  ciudades: [
    { name: "Temuco (Chile)", count: 44 },
    { name: "Santiago (Chile)", count: 120 },
    { name: "Valparaíso (Chile)", count: 30 },
    { name: "Concepción (Chile)", count: 25 }
  ]
};

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
  isError?: boolean;
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
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || `http://${window.location.hostname}:8059`;
      console.log("Conectando a API en:", apiUrl);

      const res = await fetch(`${apiUrl}/api/v1/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: query }),
      });

      const data = await res.json();

      if (!res.ok) {
        // Leer el JSON de diagnóstico devuelto por el backend refactorizado
        const errorType = data?.error_type || "UNKNOWN";
        const cause = data?.cause || "";
        console.error(`[${errorType}] Error del backend:`, cause, "\n--- Stack ---\n", data?.stack_trace);

        const friendlyMessages: Record<string, string> = {
          LLM_UNAVAILABLE: "El modelo de IA está saturado en este momento. Espera unos segundos e intenta de nuevo.",
          LLM_RATE_LIMIT: "Se ha agotado la cuota de la API. Intenta en unos minutos.",
          LLM_MODEL_NOT_FOUND: "Error de configuración: el modelo de IA no está disponible.",
          EXTERNAL_SERVICE_UNREACHABLE: "No se pudo conectar con la base de datos de búsqueda. Verifica que los servicios estén activos.",
          EXTERNAL_SERVICE_TIMEOUT: "El servicio tardó demasiado en responder. Intenta de nuevo.",
          SESSION_STORE_ERROR: "Error al recuperar tu sesión. Recarga la página e intenta de nuevo.",
          ORCHESTRATOR_RUNTIME_ERROR: "Error interno del servidor al procesar tu mensaje.",
        };

        throw new Error(friendlyMessages[errorType] || `Error del servidor (${res.status}).`);
      }

      console.log("Respuesta recibida:", data);

      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingId
            ? { 
                id: Date.now().toString(), 
                role: "assistant", 
                content: data.response || "No recibí una respuesta clara del asistente.",
                documents: data.documents,
                rich_cards: data.rich_cards,
                quick_replies: data.quick_replies
              }
            : msg
        )
      );
    } catch (error: any) {
      console.log("Error en la búsqueda:", error);
      const isNetworkError = error.message?.includes("Failed to fetch") || error.message?.includes("NetworkError");
      const errorMessage = isNetworkError 
        ? "No pudimos conectar con el servidor. Verifica que el backend (Docker) esté corriendo."
        : (error.message || "Ocurrió un error al procesar tu solicitud. Por favor, intenta de nuevo.");
        
      setMessages((prev) =>
        prev.map((msg) =>
          msg.id === loadingId
            ? { 
                id: Date.now().toString(), 
                role: "assistant", 
                content: errorMessage,
                isError: true
              }
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
              <img src="/uah-logo.png" alt="UAH Logo" className="h-14 w-auto object-contain drop-shadow-md" />
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
      <aside className={`fixed top-0 right-0 h-[100dvh] w-full md:w-[450px] bg-white/95 backdrop-blur-xl border-l border-gray-200/50 flex flex-col z-50 transition-transform duration-500 cubic-bezier(0.4, 0, 0.2, 1) shadow-[-10px_0_40px_rgba(0,0,0,0.05)] ${isChatOpen ? "translate-x-0" : "translate-x-full"}`}>
        {/* Chat Header */}
        <div className="bg-gradient-to-r from-[#002855] to-[#003b7a] text-white p-5 flex items-center justify-between shrink-0 shadow-sm relative overflow-hidden">
          <div className="absolute top-0 left-0 w-full h-full bg-white/5 opacity-50 blur-[2px]" />
          <div className="flex items-center gap-3 relative z-10">
            <div className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center border border-white/20 backdrop-blur-md shadow-inner overflow-hidden">
              <img src="/robot-avatar.png" alt="Asistente IA" className="w-full h-full object-cover" />
            </div>
            <div>
              <h3 className="text-sm font-semibold tracking-wide">Asistente IA</h3>
              <p className="text-[11px] text-blue-100/70 font-medium">Archivo Patrimonial</p>
            </div>
          </div>
          <button onClick={() => setIsChatOpen(false)} className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/20 flex items-center justify-center transition-colors relative z-10" aria-label="Cerrar chat">
            <X size={16} />
          </button>
        </div>

        {/* Chat Messages */}
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-5 bg-gray-50/50">
          {messages.map((msg) => (
            <div key={msg.id} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
              {msg.role === "user" ? (
                <div className="flex items-start gap-3 flex-row-reverse w-full max-w-[90%]">
                  <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center text-gray-500 shrink-0 shadow-sm">
                    <User size={14} />
                  </div>
                  <div className="bg-gradient-to-br from-[#f37021] to-[#e0621a] text-white px-4 py-3 rounded-2xl rounded-tr-sm text-[14px] leading-relaxed shadow-md font-medium">
                    {msg.content}
                  </div>
                </div>
              ) : (
                <div className="flex items-start gap-3 w-full">
                  <div className="w-8 h-8 rounded-full bg-[#003366] flex items-center justify-center text-white text-[9px] font-bold tracking-widest shrink-0 shadow-md overflow-hidden">
                    <img src="/robot-avatar.png" alt="Bot" className="w-full h-full object-cover" />
                  </div>
                  
                  {msg.isError ? (
                    <div className="bg-red-50/80 backdrop-blur-sm border border-red-200 text-red-800 rounded-2xl rounded-tl-sm p-4 flex items-start gap-3 w-full shadow-sm max-w-[95%]">
                      <WifiOff className="w-5 h-5 text-red-500 mt-0.5 shrink-0" />
                      <div>
                        <h4 className="font-semibold text-[13px] mb-1 text-red-900">Error de conexión</h4>
                        <p className="text-[13px] leading-relaxed opacity-90">{msg.content}</p>
                      </div>
                    </div>
                  ) : (
                    <div className="bg-white border border-gray-100 px-4 py-3.5 rounded-2xl rounded-tl-sm text-[14px] leading-relaxed shadow-sm w-full max-w-[95%]">
                      {msg.isLoading ? (
                        <div className="flex items-center gap-2 text-gray-400">
                          <Loader2 size={16} className="animate-spin text-[#f37021]" />
                          <span className="text-xs italic">Consultando archivo...</span>
                        </div>
                      ) : (
                        <div className="chat-prose text-gray-700">
                          <ReactMarkdown 
                            remarkPlugins={[remarkGfm]}
                            components={{
                              a: ({node, ...props}) => <a {...props} target="_blank" rel="noopener noreferrer" className="text-[#f37021] hover:underline" />
                            }}
                          >
                            {msg.content}
                          </ReactMarkdown>
                        </div>
                      )}

                      {/* RICH CARDS */}
                      {msg.rich_cards && msg.rich_cards.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-gray-100">
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-3">
                            <Sparkles size={12} className="text-[#f37021]" />
                            <span>Documentos Encontrados ({msg.rich_cards.length})</span>
                          </div>
                          <div className="flex flex-col gap-3">
                            {msg.rich_cards.map((card) => (
                              <div key={card.id} className="bg-white border border-gray-100 hover:border-[#f37021]/30 rounded-xl overflow-hidden transition-all duration-300 hover:shadow-lg group">
                                {card.miniatura_url && (
                                  <div className="w-full h-28 bg-gray-100 overflow-hidden">
                                    <img src={card.miniatura_url} alt={card.titulo} className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" />
                                  </div>
                                )}
                                <div className="p-3">
                                  <span className="inline-block px-2 py-0.5 bg-[#f37021]/10 text-[#f37021] text-[9px] font-bold uppercase rounded-md mb-2">
                                    {card.codigo_referencia}
                                  </span>
                                  <h4 className="font-semibold text-[13px] text-gray-800 leading-snug mb-1 line-clamp-2">{card.titulo}</h4>
                                  <p className="text-xs text-gray-500 line-clamp-2 mb-3">{card.descripcion_corta}</p>
                                  <div className="flex items-center justify-between mt-auto">
                                    <span className="text-[10px] font-semibold text-gray-400 bg-gray-50 px-2 py-1 rounded-md">{Math.round((card.relevancia || 0) * 100)}% Match</span>
                                    <a href={card.url} target="_blank" rel="noopener noreferrer" className="text-[11px] font-semibold text-[#003366] hover:text-[#f37021] flex items-center gap-1 transition-colors">
                                      Ver Ficha <ExternalLink size={12} />
                                    </a>
                                  </div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* DOCUMENTS FALLBACK */}
                      {!msg.rich_cards && msg.documents && msg.documents.length > 0 && (
                        <div className="mt-4 pt-3 border-t border-gray-100">
                          <div className="flex items-center gap-1.5 text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2">
                            <FileText size={12} />
                            <span>Fuentes ({msg.documents.length})</span>
                          </div>
                          <div className="flex flex-col gap-2">
                            {msg.documents.slice(0, 3).map((doc, idx) => (
                              <a key={idx} href={doc.href} target="_blank" rel="noopener noreferrer" className="block p-2.5 rounded-lg border border-gray-100 bg-gray-50/50 hover:bg-[#f37021]/5 hover:border-[#f37021]/30 transition-colors group">
                                <div className="font-medium text-[12px] text-gray-700 line-clamp-1 group-hover:text-[#f37021] transition-colors">{doc.title}</div>
                                <div className="flex justify-between items-center mt-1">
                                  <span className="text-[10px] text-gray-400 font-medium">{((doc.relevance_score || 0) * 100).toFixed(0)}% relevancia</span>
                                  <ChevronRight size={12} className="text-gray-300 group-hover:text-[#f37021]" />
                                </div>
                              </a>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* QUICK REPLIES */}
                      {msg.quick_replies && msg.quick_replies.length > 0 && (
                        <div className="mt-4 flex flex-wrap gap-2">
                          {msg.quick_replies.map((reply, idx) => (
                            <button 
                              key={idx} 
                              onClick={() => sendMessage(reply.value)}
                              className="px-3 py-1.5 bg-white border border-[#003366]/20 text-[#003366] text-xs rounded-full hover:bg-[#003366] hover:text-white transition-colors shadow-sm font-medium"
                            >
                              {reply.label}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} className="h-2 shrink-0" />
        </div>

        {/* Chat Input */}
        <div className="p-4 bg-white/80 backdrop-blur-md border-t border-gray-100 shrink-0 shadow-[0_-10px_20px_rgba(0,0,0,0.02)] relative">
          <QuickExplorationMenu 
            data={exploreData} 
            onSelect={(term) => {
              if (!isTyping) {
                sendMessage(term);
              }
            }} 
          />
          <form onSubmit={handleChatSubmit} className="flex items-center gap-2 bg-gray-50/80 border border-gray-200/80 rounded-2xl p-1.5 focus-within:bg-white focus-within:border-[#f37021]/50 focus-within:ring-4 focus-within:ring-[#f37021]/10 transition-all duration-300 shadow-inner mt-2">
            <input
              ref={chatInputRef}
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Pregunta sobre el archivo patrimonial..."
              className="flex-1 bg-transparent border-none outline-none text-[13px] px-3 py-2 text-gray-700 placeholder-gray-400"
              disabled={isTyping}
            />
            <button type="submit" disabled={!input.trim() || isTyping} className="w-9 h-9 rounded-xl bg-gradient-to-br from-[#f37021] to-[#e0621a] text-white flex items-center justify-center disabled:opacity-50 disabled:cursor-not-allowed hover:shadow-lg hover:shadow-[#f37021]/30 transition-all duration-300" aria-label="Enviar">
              <Send size={15} className={`${!input.trim() || isTyping ? '' : 'translate-x-[1px] -translate-y-[1px]'} transition-transform`} />
            </button>
          </form>
          <div className="text-center mt-3 text-[9px] font-semibold text-gray-400 uppercase tracking-widest flex items-center justify-center gap-1.5">
            <Sparkles size={10} className="text-[#003366]/40" />
            Powered by IA Patrimonial
          </div>
        </div>
      </aside>

      {/* ═══════════════ FLOATING OPEN BUTTON ═══════════════ */}
      {!isChatOpen && (
        <button 
          onClick={() => setIsChatOpen(true)} 
          className="fixed bottom-5 right-5 z-50 flex items-center justify-center gap-2.5 w-[165px] h-[52px] bg-[#F5F5F1] rounded-[30px] shadow-[0_4px_16px_rgba(0,0,0,0.1)] hover:bg-[#fff4ed] hover:shadow-[0_6px_24px_rgba(243,112,33,0.18)] active:scale-95 active:shadow-md transition-all duration-300 border border-black/5 group"
          aria-label="Abrir chat del Archivo"
        >
          <div className="flex items-center justify-center text-[#f37021] group-hover:scale-110 transition-transform duration-300">
            <Bot size={22} strokeWidth={2.2} />
          </div>
          <span className="text-[#2d2d2d] font-semibold text-[15px] tracking-wide mt-[1px]">
            Asistente IA
          </span>
        </button>
      )}
    </div>
  );
}
