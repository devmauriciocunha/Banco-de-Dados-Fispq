import React, { useState, useEffect } from 'react';
import { Search, AlertTriangle, Flame, Eye, Shield, Download, FileText, Droplets, Wind, Thermometer } from 'lucide-react';

const FISPQViewer = () => {
  const [selectedSubstance, setSelectedSubstance] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  const [uploadedData, setUploadedData] = useState(null);
  const [activeTab, setActiveTab] = useState('primeiros-socorros');

  // Dados de exemplo com a nova estrutura
  const exampleSubstances = [
    {
      arquivo: "acetato_iso_amila.pdf",
      data_processamento: "2024-08-18T10:30:00",
      identificacao: {
        substancia: "ACETATO DE (ISO) AMILA",
        numero_onu: "1104",
        classe_risco: "3",
        numero_risco: "30"
      },
      emergencia: {
        primeiros_socorros: {
          inalacao: "Remover para local ventilado. Eventualmente, respiração artificial.",
          contato_pele: "Lavar com água. Retirar as roupas contaminadas.",
          contato_olhos: "Lavar com bastante água, por 15 min. Procurar um oftalmologista.",
          ingestao: "Cuidado em caso de vômito. Perigo de aspiração! Procurar auxílio médico imediatamente.",
          sintomas: "Por inalação, causa sonolência, vertigens. Depois do contato com a pele pode causar efeito desengordurante.",
          notas_medico: "Tratamento sintomático. Não há antídoto específico."
        },
        combate_incendio: {
          meios_extincao: "CO2, espuma, pó",
          perigos_especificos: "Líquido inflamável",
          protecao_equipe: "Utilizar equipamento de proteção individual e equipamento de proteção respiratória autônoma"
        }
      },
      propriedades: {
        aspecto: "Líquido límpido, incolor",
        odor: "próprio",
        ph: "neutro",
        ponto_fusao: "-78,5 ºC (-109,3 ºF)",
        ponto_ebulicao: "137,0 ºC",
        ponto_fulgor: "33ºC",
        densidade: "0,870",
        solubilidade: "em água: pouco solúvel. Solúvel em etanol, éter, solventes orgânicos"
      },
      manuseio_armazenamento: {
        precaucoes_manuseio: "Manipular o produto respeitando as regras gerais de segurança",
        condicoes_armazenamento: "Manter as embalagens bem fechadas, local seco e limpo. Temperatura ambiente. Afastar de fontes de ignição."
      }
    },
    {
      arquivo: "acetato_bario.pdf",
      data_processamento: "2024-08-18T10:31:00",
      identificacao: {
        substancia: "ACETATO DE BÁRIO",
        numero_onu: "1564",
        classe_risco: "6.1",
        numero_risco: "60"
      },
      emergencia: {
        primeiros_socorros: {
          inalacao: "Remover para local ventilado. Em caso de parada respiratória: respiração artificial ou ventilação com aparelhagem. Chamar um médico",
          contato_pele: "Lavar com bastante água. Retirar as roupas contaminadas.",
          contato_olhos: "Lavar com bastante água, por 15 min. Consultar um oftalmologista, se necessário.",
          ingestao: "Beber imediatamente muita água. Chamar um médico. Administração posterior de: sulfato de sódio (1 colher de sopa / ¼ litro de água).",
          sintomas: "Após a ingestão: dores gastrointestinais, absorção",
          notas_medico: "Tratamento sintomático. Não há antídoto específico."
        },
        combate_incendio: {
          meios_extincao: "Não combustível",
          perigos_especificos: "Não disponível",
          protecao_equipe: "Não disponível"
        }
      },
      propriedades: {
        aspecto: "sólido, cristal, branco",
        odor: "inodoro",
        ph: "6,5 – 8,5",
        ponto_fusao: "~450ºC",
        solubilidade: "em água: 720 g/l"
      },
      manuseio_armazenamento: {
        precaucoes_manuseio: "Manipular o produto respeitando as regras gerais de segurança",
        condicoes_armazenamento: "Manter as embalagens bem fechadas, local seco e limpo. Temperatura ambiente"
      }
    }
  ];

  const [substances, setSubstances] = useState(exampleSubstances);

  // Função para carregar dados do consolidado.json
  const handleFileUpload = async (event) => {
    const file = event.target.files[0];
    if (file && file.type === 'application/json') {
      try {
        const text = await file.text();
        const data = JSON.parse(text);
        if (Array.isArray(data)) {
          setSubstances(data);
          setUploadedData(data);
          setSelectedSubstance(0);
        } else {
          alert('Formato de arquivo inválido. Esperado um array de objetos.');
        }
      } catch (error) {
        alert('Erro ao ler o arquivo JSON: ' + error.message);
      }
    }
  };

  const filteredSubstances = substances.filter(substance =>
    substance.identificacao?.substancia?.toLowerCase().includes(searchTerm.toLowerCase()) ||
    substance.identificacao?.numero_onu?.includes(searchTerm)
  );

  const getRiskColor = (classe) => {
    switch (classe) {
      case "3": return "bg-orange-100 text-orange-800 border-orange-300";
      case "6.1": return "bg-red-100 text-red-800 border-red-300";
      case "6": return "bg-red-100 text-red-800 border-red-300";
      case "8": return "bg-purple-100 text-purple-800 border-purple-300";
      case "4": return "bg-yellow-100 text-yellow-800 border-yellow-300";
      default: return "bg-gray-100 text-gray-800 border-gray-300";
    }
  };

  const getRiskIcon = (classe) => {
    switch (classe) {
      case "3": return <Flame className="w-4 h-4" />;
      case "6.1": case "6": return <AlertTriangle className="w-4 h-4" />;
      case "8": return <Droplets className="w-4 h-4" />;
      default: return <Shield className="w-4 h-4" />;
    }
  };

  const currentSubstance = filteredSubstances[selectedSubstance] || filteredSubstances[0];

  const exportData = () => {
    const dataStr = JSON.stringify(substances, null, 2);
    const dataUri = 'data:application/json;charset=utf-8,'+ encodeURIComponent(dataStr);
    const exportFileDefaultName = 'fispq_data.json';
    const linkElement = document.createElement('a');
    linkElement.setAttribute('href', dataUri);
    linkElement.setAttribute('download', exportFileDefaultName);
    linkElement.click();
  };

  const tabs = [
    { id: 'primeiros-socorros', label: 'Primeiros Socorros', icon: Eye },
    { id: 'combate-incendio', label: 'Combate a Incêndio', icon: Flame },
    { id: 'propriedades', label: 'Propriedades', icon: Thermometer },
    { id: 'manuseio', label: 'Manuseio', icon: Shield }
  ];

  return (
    <div className="max-w-7xl mx-auto p-6 bg-gray-50 min-h-screen">
      <div className="bg-white rounded-lg shadow-lg overflow-hidden">
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-6">
          <div className="flex justify-between items-start">
            <div>
              <h1 className="text-3xl font-bold mb-2">Sistema FISPQ Avançado</h1>
              <p className="text-blue-100">Fichas de Informações de Segurança de Produtos Químicos</p>
            </div>
            <div className="flex gap-3">
              <label className="bg-white text-blue-600 px-4 py-2 rounded-lg cursor-pointer hover:bg-blue-50 transition-colors flex items-center gap-2">
                <FileText className="w-4 h-4" />
                Carregar JSON
                <input 
                  type="file" 
                  accept=".json" 
                  onChange={handleFileUpload} 
                  className="hidden" 
                />
              </label>
              <button 
                onClick={exportData}
                className="bg-green-500 text-white px-4 py-2 rounded-lg hover:bg-green-600 transition-colors flex items-center gap-2"
              >
                <Download className="w-4 h-4" />
                Exportar
              </button>
            </div>
          </div>
        </div>

        <div className="p-6">
          {/* Barra de Pesquisa */}
          <div className="relative mb-6">
            <Search className="absolute left-3 top-3 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Pesquisar por substância ou número ONU..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent text-lg"
            />
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-4 gap-6">
            {/* Lista de Substâncias */}
            <div className="xl:col-span-1">
              <h2 className="text-xl font-semibold mb-4">Substâncias ({filteredSubstances.length})</h2>
              <div className="space-y-2 max-h-96 overflow-y-auto">
                {filteredSubstances.map((substance, index) => (
                  <button
                    key={substance.arquivo}
                    onClick={() => setSelectedSubstance(index)}
                    className={`w-full text-left p-4 rounded-lg border transition-all duration-200 ${
                      selectedSubstance === index
                        ? 'bg-blue-50 border-blue-300 text-blue-900 transform scale-[1.02]'
                        : 'bg-white border-gray-200 hover:bg-gray-50 hover:border-gray-300'
                    }`}
                  >
                    <div className="font-medium text-sm mb-2 line-clamp-2">
                      {substance.identificacao?.substancia || 'Nome não disponível'}
                    </div>
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`inline-flex items-center gap-1 px-2 py-1 rounded text-xs border ${getRiskColor(substance.identificacao?.classe_risco)}`}>
                        {getRiskIcon(substance.identificacao?.classe_risco)}
                        Classe {substance.identificacao?.classe_risco}
                      </span>
                    </div>
                    <div className="text-xs text-gray-500">
                      ONU: {substance.identificacao?.numero_onu || 'N/A'}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Detalhes da Substância */}
            <div className="xl:col-span-3">
              {currentSubstance && (
                <div className="space-y-6">
                  {/* Cabeçalho da Substância */}
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 p-6 rounded-lg border border-blue-100">
                    <h2 className="text-2xl font-bold text-gray-900 mb-3">
                      {currentSubstance.identificacao?.substancia || 'Nome não disponível'}
                    </h2>
                    <div className="grid grid-cols-2 md:grid-cols-5 gap-4 text-sm">
                      <div>
                        <span className="text-gray-500 block">Número ONU:</span>
                        <div className="font-semibold text-lg">{currentSubstance.identificacao?.numero_onu || 'N/A'}</div>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Classe:</span>
                        <div className="font-semibold text-lg">{currentSubstance.identificacao?.classe_risco || 'N/A'}</div>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Risco:</span>
                        <div className="font-semibold text-lg">{currentSubstance.identificacao?.numero_risco || 'N/A'}</div>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Aspecto:</span>
                        <div className="font-semibold">{currentSubstance.propriedades?.aspecto || 'N/A'}</div>
                      </div>
                      <div>
                        <span className="text-gray-500 block">Processado:</span>
                        <div className="font-semibold text-xs">
                          {currentSubstance.data_processamento ? 
                            new Date(currentSubstance.data_processamento).toLocaleDateString('pt-BR') : 'N/A'}
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Abas de Navegação */}
                  <div className="flex flex-wrap gap-2 mb-4">
                    {tabs.map((tab) => {
                      const Icon = tab.icon;
                      return (
                        <button
                          key={tab.id}
                          onClick={() => setActiveTab(tab.id)}
                          className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
                            activeTab === tab.id
                              ? 'bg-blue-500 text-white'
                              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                          }`}
                        >
                          <Icon className="w-4 h-4" />
                          {tab.label}
                        </button>
                      );
                    })}
                  </div>

                  {/* Conteúdo das Abas */}
                  <div className="bg-white border border-gray-200 rounded-lg p-6">
                    {activeTab === 'primeiros-socorros' && (
                      <div>
                        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                          <Eye className="w-5 h-5 text-green-600" />
                          Primeiros Socorros
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          {Object.entries(currentSubstance.emergencia?.primeiros_socorros || {}).map(([key, value]) => {
                            const labels = {
                              inalacao: 'Inalação',
                              contato_pele: 'Contato com a Pele',
                              contato_olhos: 'Contato com os Olhos',
                              ingestao: 'Ingestão',
                              sintomas: 'Sintomas e Efeitos',
                              notas_medico: 'Notas para o Médico'
                            };
                            return (
                              <div key={key} className="border border-red-200 rounded-lg p-4 bg-red-50">
                                <h4 className="font-medium text-red-800 mb-2 flex items-center gap-2">
                                  <Wind className="w-4 h-4" />
                                  {labels[key] || key}:
                                </h4>
                                <p className="text-sm text-gray-700 leading-relaxed">{value}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {activeTab === 'combate-incendio' && (
                      <div>
                        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                          <Flame className="w-5 h-5 text-orange-600" />
                          Combate a Incêndio
                        </h3>
                        <div className="space-y-4">
                          {Object.entries(currentSubstance.emergencia?.combate_incendio || {}).map(([key, value]) => {
                            const labels = {
                              meios_extincao: 'Meios de Extinção',
                              perigos_especificos: 'Perigos Específicos',
                              protecao_equipe: 'Proteção da Equipe'
                            };
                            return (
                              <div key={key} className="border border-orange-200 rounded-lg p-4 bg-orange-50">
                                <h4 className="font-medium text-orange-800 mb-2">{labels[key] || key}:</h4>
                                <p className="text-sm text-gray-700 leading-relaxed">{value}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {activeTab === 'propriedades' && (
                      <div>
                        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                          <Thermometer className="w-5 h-5 text-purple-600" />
                          Propriedades Físico-Químicas
                        </h3>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                          {Object.entries(currentSubstance.propriedades || {}).map(([key, value]) => {
                            const labels = {
                              aspecto: 'Aspecto',
                              odor: 'Odor',
                              ph: 'pH',
                              ponto_fusao: 'Ponto de Fusão',
                              ponto_ebulicao: 'Ponto de Ebulição',
                              ponto_fulgor: 'Ponto de Fulgor',
                              densidade: 'Densidade',
                              solubilidade: 'Solubilidade'
                            };
                            const icons = {
                              aspecto: Eye, odor: Wind, ph: Thermometer,
                              ponto_fusao: Thermometer, ponto_ebulicao: Thermometer,
                              ponto_fulgor: Flame, densidade: Shield, solubilidade: Droplets
                            };
                            const Icon = icons[key] || Thermometer;
                            return (
                              <div key={key} className="border border-purple-200 rounded-lg p-4 bg-purple-50">
                                <h4 className="font-medium text-purple-800 mb-2 flex items-center gap-2">
                                  <Icon className="w-4 h-4" />
                                  {labels[key] || key}:
                                </h4>
                                <p className="text-sm text-gray-700 font-mono">{value}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}

                    {activeTab === 'manuseio' && (
                      <div>
                        <h3 className="text-xl font-semibold mb-4 flex items-center gap-2">
                          <Shield className="w-5 h-5 text-blue-600" />
                          Manuseio e Armazenamento
                        </h3>
                        <div className="space-y-4">
                          {Object.entries(currentSubstance.manuseio_armazenamento || {}).map(([key, value]) => {
                            const labels = {
                              precaucoes_manuseio: 'Precauções para o Manuseio Seguro',
                              condicoes_armazenamento: 'Condições de Armazenamento Seguro'
                            };
                            return (
                              <div key={key} className="border border-blue-200 rounded-lg p-4 bg-blue-50">
                                <h4 className="font-medium text-blue-800 mb-2">{labels[key] || key}:</h4>
                                <p className="text-sm text-gray-700 leading-relaxed">{value}</p>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default FISPQViewer;