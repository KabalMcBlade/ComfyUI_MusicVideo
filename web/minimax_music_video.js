import { app } from "../../scripts/app.js";
import { api } from "../../scripts/api.js";

const STYLE = `
.h3mv{box-sizing:border-box;width:100%;height:100%;min-width:0;min-height:0;overflow:auto;padding:12px;background:#0c1119;color:#e9f0f7;font:12px/1.4 system-ui;border:1px solid #33445b;border-radius:8px}.h3mv *{box-sizing:border-box}.h3mv h3{margin:0;color:#76d8df}.h3mv section{margin-top:10px;padding:10px;background:#131c29;border:1px solid #314258;border-radius:7px}.h3mv label{display:grid;gap:4px;color:#aebed1}.h3mv input,.h3mv select,.h3mv textarea,.h3mv button{padding:6px;background:#09101a;color:#eef5fb;border:1px solid #40546d;border-radius:5px}.h3mv textarea{width:100%;min-height:220px;resize:vertical;font:12px/1.4 ui-monospace,monospace}.h3mv button{cursor:pointer;background:#263950}.h3mv-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px}.h3mv-ref{position:relative;min-height:150px;display:grid;place-items:center;overflow:hidden;background:#080d14;border:1px dashed #526a87;border-radius:7px;cursor:pointer}.h3mv-ref img{width:100%;height:130px;object-fit:contain}.h3mv-ref span{padding:8px;text-align:center;word-break:break-all}.h3mv-remove{position:absolute;top:5px;right:5px;z-index:2;padding:2px 7px!important;background:#7c2932!important}.h3mv-audio{display:flex;align-items:center;gap:8px;flex-wrap:wrap}.h3mv-shots{white-space:pre-wrap;font:12px/1.55 ui-monospace,monospace;color:#cbd8e6}.h3mv-muted{color:#8fa1b6}.h3mv-progress{color:#79d8a6}.h3mv details summary{cursor:pointer;color:#c7d7e8;margin-bottom:8px}@container(max-width:560px){.h3mv-grid{grid-template-columns:1fr}}
`;

const names=["master_audio","chunk_size","picture_1","picture_2","picture_3","picture_4","prompt","aspect_ratio","megapixels","project_name","global_seed","steps","model_name","text_encoder","video_vae","audio_vae","turbo_lora","ffmpeg_executable","save_shot_previews","stitch_final_video","shot_index","enable_upscale"];
const advanced=["shot_index","enable_upscale","project_name","global_seed","steps","model_name","text_encoder","video_vae","audio_vae","turbo_lora","ffmpeg_executable","save_shot_previews","stitch_final_video"];
const widget=(node,name)=>node.widgets?.find(item=>item.name===name);
const get=(node,name,fallback="")=>widget(node,name)?.value??fallback;
const set=(node,name,value)=>{const item=widget(node,name);if(item){item.value=value;item.callback?.(value);}node.setDirtyCanvas(true,true);};
const control=(type,value)=>{const el=document.createElement("input");el.type=type;el.value=value;return el;};
const label=(text,el)=>{const wrap=document.createElement("label");wrap.append(text,el);return wrap;};
const upload=async(file)=>{const data=new FormData();data.append("image",file);data.append("type","input");data.append("subfolder","minimax_h3_music_video");const response=await fetch("/upload/image",{method:"POST",body:data});if(!response.ok)throw new Error(`Upload failed (${response.status})`);const result=await response.json();return result.subfolder?`${result.subfolder}/${result.name}`:result.name;};
const mediaUrl=(name)=>{const parts=String(name).replaceAll("\\","/").split("/");const filename=parts.pop();const subfolder=parts.join("/");return api.apiURL(`/view?filename=${encodeURIComponent(filename)}&type=input&subfolder=${encodeURIComponent(subfolder)}`);};
const stamp=(seconds)=>{const minutes=Math.floor(seconds/60),secs=seconds-minutes*60;return `${String(minutes).padStart(2,"0")}:${secs.toFixed(2).padStart(5,"0")}`;};

function attach(node){
  const refreshers=[];
  for(const name of names){
    const item=widget(node,name);
    if(!item)continue;
    item.hidden=true;
    item._h3mvComputeSize??=item.computeSize;
    item.computeSize=()=>[0,-4];
  }
  const root=document.createElement("div");root.className="h3mv";root.style.containerType="inline-size";
  const head=document.createElement("div"),status=document.createElement("span");head.style.cssText="display:flex;justify-content:space-between;gap:8px";head.innerHTML="<h3>MiniMax H3 Music Video</h3>";status.className="h3mv-progress";status.textContent="Ready";head.append(status);root.append(head);

  let duration=0;
  const audioSection=document.createElement("section"),audioRow=document.createElement("div"),audioButton=document.createElement("button"),audioName=document.createElement("span"),durationText=document.createElement("span"),audioInput=control("file","");audioRow.className="h3mv-audio";audioInput.accept="audio/*";audioInput.hidden=true;audioButton.textContent="Upload / Replace Audio";audioName.textContent=get(node,"master_audio")||"No master audio";durationText.className="h3mv-muted";durationText.textContent="Duration: —";audioRow.append(audioButton,audioName,durationText,audioInput);audioSection.append(audioRow);root.append(audioSection);
  const chunk=control("number",get(node,"chunk_size",5));chunk.min="0.01";chunk.step="0.01";const shotText=document.createElement("div");shotText.className="h3mv-shots";const shotSection=document.createElement("section");shotSection.append(label("Chunk Size (seconds)",chunk),document.createElement("hr"),shotText);root.append(shotSection);
  refreshers.push(()=>{chunk.value=String(get(node,"chunk_size",5));});
  const renderShots=()=>{const size=Number(chunk.value);if(!(duration>0&&size>0)){shotText.textContent="SHOT LIST\nUpload audio to calculate shots.";return;}const lines=["SHOT LIST"];for(let i=0;i<Math.ceil(duration/size);i++){const start=i*size,end=Math.min(duration,(i+1)*size);lines.push(`#${i+1}   ${stamp(start)} - ${stamp(end)}    ${(end-start).toFixed(2)} s`);}shotText.textContent=lines.join("\n");};
  const readDuration=(source)=>new Promise((resolve,reject)=>{const audio=document.createElement("audio");audio.preload="metadata";audio.onloadedmetadata=()=>resolve(audio.duration);audio.onerror=reject;audio.src=source;});
  let audioRefresh=0;
  const refreshAudio=()=>{const generation=++audioRefresh,name=String(get(node,"master_audio")||"");audioName.textContent=name||"No master audio";duration=0;durationText.textContent="Duration: —";if(!name){renderShots();return;}readDuration(mediaUrl(name)).then(value=>{if(generation!==audioRefresh)return;duration=value;durationText.textContent=`Duration: ${value.toFixed(2)} s`;renderShots();}).catch(()=>{if(generation===audioRefresh)renderShots();});};
  const selectAudio=async(file)=>{try{status.textContent="Uploading audio…";const name=await upload(file);set(node,"master_audio",name);refreshAudio();status.textContent="Ready";}catch(error){status.textContent=error.message;}};
  audioButton.onclick=()=>audioInput.click();audioInput.onchange=()=>audioInput.files[0]&&selectAudio(audioInput.files[0]);audioSection.ondragover=e=>e.preventDefault();audioSection.ondrop=e=>{e.preventDefault();const file=[...e.dataTransfer.files].find(item=>item.type.startsWith("audio/"));if(file)selectAudio(file);};chunk.oninput=()=>{set(node,"chunk_size",Number(chunk.value));renderShots();};
  refreshers.push(refreshAudio);

  const refs=document.createElement("section"),refGrid=document.createElement("div");refs.append("REFERENCE IMAGES",refGrid);refGrid.className="h3mv-grid";root.append(refs);
  for(let index=1;index<=4;index++){const name=`picture_${index}`,slot=document.createElement("div"),fileInput=control("file","");slot.className="h3mv-ref";fileInput.accept="image/*";fileInput.hidden=true;const draw=()=>{slot.replaceChildren(fileInput);const value=get(node,name);if(value){const image=document.createElement("img"),remove=document.createElement("button");image.src=mediaUrl(value);image.alt=`Picture ${index}`;remove.className="h3mv-remove";remove.textContent="×";remove.title="Remove";remove.onclick=e=>{e.stopPropagation();set(node,name,"");draw();};slot.append(image,remove);}else{const text=document.createElement("span");text.textContent=`Picture ${index}\nDrop or click to upload`;slot.append(text);}};const choose=async(file)=>{if(!file?.type.startsWith("image/"))return;status.textContent=`Uploading Picture ${index}…`;try{set(node,name,await upload(file));draw();status.textContent="Ready";}catch(error){status.textContent=error.message;}};slot.onclick=e=>{if(e.target!==fileInput)e.currentTarget.querySelector("input").click();};slot.ondragover=e=>e.preventDefault();slot.ondrop=e=>{e.preventDefault();e.stopPropagation();choose(e.dataTransfer.files[0]);};fileInput.onchange=()=>choose(fileInput.files[0]);refreshers.push(draw);refGrid.append(slot);}

  const prompt=document.createElement("textarea");prompt.placeholder="subject_definitions:\n...\n\n[Shot 1] ...\n[Shot 2] ...\n\noverall_soundscape:\n...";prompt.oninput=()=>set(node,"prompt",prompt.value);refreshers.push(()=>{prompt.value=String(get(node,"prompt")||"");});const promptSection=document.createElement("section");promptSection.append(label("Structured MiniMax REF2VA Prompt",prompt));root.append(promptSection);
  const settings=document.createElement("section"),mainGrid=document.createElement("div");mainGrid.className="h3mv-grid";const aspect=document.createElement("select");for(const value of ["16:9","9:16","1:1","4:3","3:4","21:9"]){const option=document.createElement("option");option.value=option.textContent=value;aspect.append(option);}aspect.onchange=()=>set(node,"aspect_ratio",aspect.value);refreshers.push(()=>{aspect.value=String(get(node,"aspect_ratio","16:9"));});const mp=control("number",get(node,"megapixels",1));mp.min="0.1";mp.max="2";mp.step="0.05";const commitMegapixels=()=>{const value=Number(mp.value);if(Number.isFinite(value))set(node,"megapixels",value);};mp.oninput=commitMegapixels;mp.onchange=commitMegapixels;refreshers.push(()=>{mp.value=String(get(node,"megapixels",1));});mainGrid.append(label("Aspect Ratio",aspect),label("Megapixels",mp));settings.append(mainGrid);const details=document.createElement("details"),summary=document.createElement("summary"),advancedGrid=document.createElement("div");summary.textContent="Advanced";advancedGrid.className="h3mv-grid";details.append(summary,advancedGrid);for(const name of advanced){const original=widget(node,name),type=typeof original?.value==="boolean"?"checkbox":typeof original?.value==="number"?"number":"text",el=control(type,"");if(name==="shot_index"){el.min="-1";el.step="1";el.title="-1 renders every shot; otherwise enter the displayed 1-based shot number";}const commit=()=>{if(type==="checkbox")set(node,name,el.checked);else if(type==="number"){const value=Number(el.value);if(Number.isFinite(value))set(node,name,value);}else set(node,name,el.value);};el.oninput=commit;el.onchange=commit;refreshers.push(()=>{if(type==="checkbox")el.checked=Boolean(get(node,name));else el.value=String(get(node,name)??"");});const text=name==="shot_index"?"Shot to generate (-1 = all)":name==="enable_upscale"?"Upscale to HD (matches aspect ratio)":name.replaceAll("_"," ");advancedGrid.append(label(text,el));}settings.append(details);root.append(settings);
  const minimumPanelHeight=360;
  let domWidget;
  const panelHeight=()=>{
    const nodeHeight=Number(node.size?.[1])||minimumPanelHeight+80;
    const widgetTop=Number(domWidget?.last_y);
    const top=Number.isFinite(widgetTop)&&widgetTop>0?widgetTop:70;
    return Math.max(minimumPanelHeight,nodeHeight-top-8);
  };
  domWidget=node.addDOMWidget("minimax_h3_ui","div",root,{
    serialize:false,
    hideOnZoom:false,
    getMinHeight:()=>minimumPanelHeight,
    getMaxHeight:panelHeight,
    getHeight:panelHeight,
  });
  node.resizable=true;
  const originalResize=node.onResize;
  node.onResize=function(size){
    originalResize?.call(this,size);
    root.style.width="100%";
    root.style.height="100%";
  };
  const refreshVisibleState=()=>{for(const refresh of refreshers)refresh();status.textContent="Ready";};
  const originalConfigure=node.onConfigure;
  node.onConfigure=function(info){
    originalConfigure?.call(this,info);
    queueMicrotask(refreshVisibleState);
  };
  refreshVisibleState();
  node._h3mvStatus=status;
}

if(!document.getElementById("h3mv-style")){const style=document.createElement("style");style.id="h3mv-style";style.textContent=STYLE;document.head.append(style);}
api.addEventListener("minimax_h3_music_video_progress",event=>{const data=event.detail;for(const node of app.graph?._nodes||[]){if(node.type==="MiniMaxH3MusicVideo"&&String(node.id)===String(data.node)){node._h3mvStatus.textContent=data.stage==="Complete"?"Complete":`Shot ${data.shot}/${data.total} · ${data.stage}`;}}});
app.registerExtension({name:"music-video.minimax-h3",beforeRegisterNodeDef(nodeType,nodeData){if(nodeData.name!=="MiniMaxH3MusicVideo")return;const created=nodeType.prototype.onNodeCreated;nodeType.prototype.onNodeCreated=function(){created?.apply(this,arguments);attach(this);};}});
