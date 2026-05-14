"use client";

import { useState, useRef, useEffect } from "react";
import { Send, Search, ExternalLink, Bot, User, Loader2, BookOpen, Info, Library } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ArchiveDocument {
  id: string;
  title: string;
  href: string;
  description: string;
  relevance_score?: number;
}

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  documents?: ArchiveDocument[];
  isLoading?: boolean;
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "welcome",
      role: "assistant",
      content: "### Bienvenido al Buscador Inteligente del Archivo Patrimonial UAH\n\n¿Qué documentación patrimonial estás buscando hoy? Puedes consultar por temas, personas o fondos específicos.",
    },
  ]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isTyping) return;

    const userMessage: Message = { id: Date.now().toString(), role: "user", content: input };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsTyping(true);

    const loadingId = "loading-" + Date.now();
    setMessages((prev) => [...prev, { id: loadingId, role: "assistant", content: "", isLoading: true }]);

    try {
      // Detección automática de la URL del API Gateway
      const host = typeof window !== 'undefined' ? window.location.hostname : 'localhost';
      const apiUrl = `http://${host}:3000`;
      
      const res = await fetch(`${apiUrl}/api/v1/chat/message`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message: userMessage.content }),
      });

      if (!res.ok) throw new Error("Error en la respuesta del servidor");

      const data = await res.json();
      
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === loadingId 
            ? { id: Date.now().toString(), role: "assistant", content: data.response, documents: data.documents }
            : msg
        )
      );
    } catch (error) {
      console.error(error);
      setMessages((prev) => 
        prev.map((msg) => 
          msg.id === loadingId 
            ? { id: Date.now().toString(), role: "assistant", content: "❌ **Error de conexión con el Archivo**: No se pudo contactar con el servidor. Por favor, asegúrate de que el sistema esté encendido mediante Docker y que la API sea accesible." }
            : msg
        )
      );
    } finally {
      setIsTyping(false);
    }
  };

  return (
    <div className="min-h-screen flex flex-col font-sans">
      
      {/* 1. CABECERA INSTITUCIONAL (ESTILO UAH) */}
      <header className="uah-official-header">
        <div className="flex items-center justify-between w-full">
          <div className="flex items-center gap-4">
            {/* Simulación del logo de la universidad */}
            <div className="bg-white p-1 rounded-full w-12 h-12 flex items-center justify-center border-2 border-orange-500">
               <span className="text-black font-black text-xs">UAH</span>
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-sm tracking-widest uppercase">Universidad Alberto Hurtado</span>
              <span className="text-[#f37021] font-bold text-xs uppercase tracking-tighter">Archivo Patrimonial</span>
            </div>
          </div>
          <nav className="hidden lg:flex items-center gap-8 text-[11px] font-bold uppercase tracking-widest">
            <a href="#" className="hover:text-[#f37021]">Quienes Somos</a>
            <a href="#" className="hover:text-[#f37021]">Sitios de Interés</a>
            <a href="#" className="hover:text-[#f37021]">Fondos</a>
            <button className="bg-white/10 hover:bg-white/20 px-4 py-2 rounded">Iniciar Sesión</button>
          </nav>
        </div>
      </header>

      {/* 2. SECCIÓN HERO / BUSCADOR (ESTILO SITIO OFICIAL) */}
      <section className="uah-hero-section">
        <div className="max-w-4xl mx-auto px-4">
          <h2 className="text-center font-bold text-2xl uppercase tracking-widest text-[#f37021] mb-6">Navegar por el Archivo</h2>
          <form onSubmit={handleSubmit} className="flex shadow-2xl">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Buscar documentación patrimonial..."
              className="uah-input-search flex-1 outline-none text-lg"
            />
            <button
              type="submit"
              disabled={!input.trim() || isTyping}
              className="btn-uah-official flex items-center gap-2"
            >
              {isTyping ? <Loader2 className="animate-spin" /> : "Buscar"}
            </button>
          </form>
          <div className="flex justify-center gap-8 mt-6">
            <div className="flex flex-col items-center gap-2 cursor-pointer group">
              <div className="w-12 h-12 rounded-full border-2 border-[#f37021] flex items-center justify-center group-hover:bg-[#f37021] group-hover:text-white transition-all text-[#f37021]">
                <BookOpen size={20} />
              </div>
              <span className="text-[10px] font-bold uppercase">Materias</span>
            </div>
            <div className="flex flex-col items-center gap-2 cursor-pointer group">
              <div className="w-12 h-12 rounded-full border-2 border-[#f37021] flex items-center justify-center group-hover:bg-[#f37021] group-hover:text-white transition-all text-[#f37021]">
                <Library size={20} />
              </div>
              <span className="text-[10px] font-bold uppercase">Fondos</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. CONTENEDOR DE RESULTADOS Y CONVERSACIÓN */}
      <main className="flex-1 bg-white">
        <div className="chat-container-clean">
          <div className="flex flex-col gap-6">
            {messages.map((msg) => (
              <div key={msg.id} className={`flex flex-col ${msg.role === "user" ? "items-end" : "items-start"}`}>
                
                {msg.role === "user" && (
                  <div className="bubble-user">
                    {msg.content}
                  </div>
                )}

                {msg.role === "assistant" && (
                  <div className="bubble-ai w-full">
                    <div className="flex items-center gap-2 mb-4 border-b border-gray-100 pb-2">
                       <Bot size={18} className="text-[#f37021]" />
                       <span className="text-[10px] font-bold uppercase tracking-widest text-gray-400">Asistente Inteligente UAH</span>
                    </div>
                    
                    {msg.isLoading ? (
                      <div className="flex items-center gap-3 py-4">
                        <Loader2 className="animate-spin text-[#f37021]" />
                        <span className="text-sm font-medium text-gray-500 italic">Buscando en los registros históricos...</span>
                      </div>
                    ) : (
                      <div className="prose prose-sm max-w-none text-gray-700 leading-relaxed">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.content}</ReactMarkdown>
                      </div>
                    )}

                    {/* TARJETAS DE RESULTADOS (DOCUMENTOS) */}
                    {msg.documents && msg.documents.length > 0 && (
                      <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-4">
                        {msg.documents.map((doc, idx) => (
                          <div key={idx} className="uah-doc-result group">
                            <a href={doc.href} target="_blank" className="uah-doc-title">
                              {doc.title}
                            </a>
                            <p className="text-xs text-gray-500 mb-4 line-clamp-3">
                              {doc.description || "Este documento pertenece al catálogo patrimonial de la UAH. Haz clic para ver los detalles completos en el sistema AtoM."}
                            </p>
                            <div className="flex justify-between items-center text-[10px] font-bold uppercase text-gray-400">
                               <span>Relevancia: {(doc.relevance_score || 0).toFixed(2)}</span>
                               <a href={doc.href} target="_blank" className="text-[#f37021] hover:underline flex items-center gap-1">
                                 Ver Documento <ExternalLink size={10} />
                               </a>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} className="h-20" />
          </div>
        </div>
      </main>

      {/* 4. FOOTER INSTITUCIONAL */}
      <footer className="bg-[#1a1a1a] text-white py-12 px-10">
        <div className="max-w-6xl mx-auto grid grid-cols-1 md:grid-cols-3 gap-10">
          <div>
            <h3 className="font-bold text-xl mb-4">UAH / Universidad Alberto Hurtado</h3>
            <p className="text-sm text-gray-400">Av. Bernardo O'Higgins 1825</p>
            <p className="text-sm text-gray-400">Santiago de Chile</p>
          </div>
          <div>
            <h4 className="font-bold text-orange-500 mb-4 uppercase text-xs tracking-widest">Sitios de Interés</h4>
            <ul className="text-sm text-gray-400 space-y-2">
              <li><a href="#" className="hover:text-white transition-colors">Ciencias Sociales</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Derecho</a></li>
              <li><a href="#" className="hover:text-white transition-colors">Economía y Negocios</a></li>
            </ul>
          </div>
          <div>
            <h4 className="font-bold text-orange-500 mb-4 uppercase text-xs tracking-widest">Contacto</h4>
            <p className="text-sm text-gray-400">Teléfono: +56 2 2692 0200</p>
          </div>
        </div>
      </footer>
    </div>
  );
}
