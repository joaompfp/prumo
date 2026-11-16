window.proofViolations=[];
document.addEventListener('securitypolicyviolation',e=>window.proofViolations.push({directive:e.violatedDirective,blocked:e.blockedURI}));
const tokens=[['3.90','1234567.80'],['4.10','1256789.00'],['2.00','1299999.90']];
const displays=[['3,90','1 234 567,80'],['4,10','1 256 789,00'],['2,00','1 299 999,90']];
const labels=['janeiro de 2026','fevereiro de 2026','março de 2026'];
const names=['Taxa, valores de teste','Stock, valores de teste'];
const units=['%','milhões de euros'];
window.proofChart=EChartsProof.init(document.getElementById('chart'),null,{renderer:'canvas'});
window.proofChart.setOption({animation:false,useUTC:true,grid:{left:52,right:90,top:50,bottom:38},
xAxis:{type:'value',min:0,max:2,interval:1,axisLabel:{formatter:v=>labels[v]?labels[v].slice(0,3):''},axisPointer:{snap:true,label:{show:false}}},
yAxis:[{type:'value',name:'%',scale:true,axisLabel:{formatter:v=>String(v).replace('.',',')}},{type:'value',name:'milhões de euros',nameLocation:'end',nameTextStyle:{align:'right'},scale:true,splitLine:{show:false}}],
tooltip:{trigger:'axis',renderMode:'richText',confine:true,axisPointer:{type:'line',label:{show:false}},formatter:params=>{const i=Math.round(params[0].value[0]);const t=labels[i]+'\n'+names.map((n,s)=>n+': '+displays[i][s]+' '+units[s]).join('\n');window.proofTooltip=t;document.getElementById('readout').textContent=t;return t;}},
series:names.map((name,s)=>({name,type:'line',smooth:false,connectNulls:false,showSymbol:true,symbolSize:8,yAxisIndex:s,lineStyle:{width:2,color:s?'#c00':'#232323'},itemStyle:{color:s?'#c00':'#232323'},data:tokens.map((v,i)=>[i,Number(v[s])])}))});
window.proofReady=true;
document.getElementById('result').textContent='Motor carregado; dois eixos. Passe o rato ou toque num ponto.';
new ResizeObserver(()=>window.proofChart.resize()).observe(document.getElementById('chart'));
