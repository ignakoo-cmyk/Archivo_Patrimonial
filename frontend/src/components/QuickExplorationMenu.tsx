"use client";

import React, { useState, useMemo } from 'react';
import { Search, ChevronDown, ChevronUp, X } from 'lucide-react';

export interface CategoryItem {
  name: string;
  count: number;
}

export interface ExplorationData {
  materias: CategoryItem[];
  personajes: CategoryItem[];
  ciudades: CategoryItem[];
}

interface QuickExplorationMenuProps {
  data: ExplorationData;
  onSelect: (term: string) => void;
}

type ActiveTab = 'materias' | 'personajes' | 'ciudades' | null;

export default function QuickExplorationMenu({ data, onSelect }: QuickExplorationMenuProps) {
  const [activeTab, setActiveTab] = useState<ActiveTab>(null);
  const [searchTerm, setSearchTerm] = useState('');

  // Normalizador sin tildes ni mayúsculas para un filtrado ultra-rápido
  const normalizeText = (text: string) => 
    text.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();

  const handleTabClick = (tab: ActiveTab) => {
    if (activeTab === tab) {
      setActiveTab(null);
      setSearchTerm('');
    } else {
      setActiveTab(tab);
      setSearchTerm('');
    }
  };

  // Referencia a la lista actual para evitar búsquedas de objeto innecesarias
  const currentList = activeTab ? data[activeTab] || [] : [];

  // useMemo es CRÍTICO aquí para evitar refiltrar miles de registros en cada render
  // (ej. cuando se mueve un pixel de scroll o cambia otro estado externo)
  const filteredList = useMemo(() => {
    if (!searchTerm.trim()) return currentList;
    
    const normalizedSearch = normalizeText(searchTerm);
    return currentList.filter(item => 
      normalizeText(item.name).includes(normalizedSearch)
    );
  }, [currentList, searchTerm]);

  const handleSelect = (term: string) => {
    setActiveTab(null);
    setSearchTerm('');
    onSelect(term);
  };

  return (
    <div className="w-full relative z-20 flex flex-col items-center pb-3 px-4">
      {/* Contenedor Desplegable (absoluto hacia arriba para sobreponerse al chat) */}
      {activeTab && (
        <div className="absolute bottom-full left-4 right-4 mb-2 bg-white rounded-2xl shadow-[0_8px_30px_rgba(0,0,0,0.12)] border border-gray-200 overflow-hidden flex flex-col transition-all duration-300 origin-bottom animate-in slide-in-from-bottom-2 fade-in">
          
          {/* Header con Buscador */}
          <div className="p-3 border-b border-gray-100 bg-gray-50/80 flex items-center gap-2">
            <Search size={16} className="text-[#f37021] flex-shrink-0" />
            <input
              type="text"
              autoFocus
              placeholder={`Buscar en ${activeTab}...`}
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="flex-1 bg-transparent border-none outline-none text-[13px] text-gray-700 placeholder-gray-400 font-medium"
            />
            <button 
              onClick={() => setActiveTab(null)}
              className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors text-gray-400 hover:text-gray-700"
              aria-label="Cerrar menú"
            >
              <X size={15} strokeWidth={2.5} />
            </button>
          </div>

          {/* Lista Virtualizada / Scroll Optimizada */}
          <div className="max-h-60 overflow-y-auto overscroll-contain flex flex-col divide-y divide-gray-50/80 scrollbar-thin scrollbar-thumb-gray-200 scrollbar-track-transparent">
            {filteredList.length === 0 ? (
              <div className="p-8 text-center text-[13px] text-gray-400 font-medium">
                No se encontraron resultados para "{searchTerm}"
              </div>
            ) : (
              filteredList.map((item, index) => (
                <button
                  key={`${item.name}-${index}`}
                  onClick={() => handleSelect(item.name)}
                  className="flex items-center justify-between p-3.5 hover:bg-[#f37021]/5 text-left transition-colors group"
                >
                  <span className="text-[13.5px] text-gray-700 font-medium group-hover:text-[#f37021] line-clamp-1 pr-4">
                    {item.name}
                  </span>
                  <span className="text-[11px] font-bold text-gray-400 bg-gray-50 px-2 py-0.5 rounded-full group-hover:bg-[#f37021]/10 group-hover:text-[#f37021] flex-shrink-0">
                    {item.count.toLocaleString()}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>
      )}

      {/* Botones Principales (Chips) */}
      <div className="flex items-center justify-center gap-2.5 w-full">
        {(['materias', 'personajes', 'ciudades'] as const).map((tab) => {
          const isActive = activeTab === tab;
          return (
            <button
              key={tab}
              onClick={() => handleTabClick(tab)}
              className={`flex items-center gap-1.5 px-4 py-1.5 rounded-full text-[11px] font-bold tracking-widest uppercase transition-all duration-300 border backdrop-blur-md
                ${isActive 
                  ? 'bg-[#f37021] text-white border-[#f37021] shadow-lg shadow-[#f37021]/25 scale-105' 
                  : 'bg-white/90 text-gray-600 border-gray-200 shadow-sm hover:border-[#f37021]/40 hover:text-[#f37021] hover:bg-gray-50/90'
                }
              `}
            >
              {tab}
              {isActive ? <ChevronDown size={14} strokeWidth={3} /> : <ChevronUp size={14} strokeWidth={2} className="opacity-50" />}
            </button>
          );
        })}
      </div>
    </div>
  );
}
