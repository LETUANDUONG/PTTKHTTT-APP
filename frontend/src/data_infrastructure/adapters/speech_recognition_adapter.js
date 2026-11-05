import {api} from '../http/api';

// The browser records audio; only the local Hoodoo backend transcribes it.
export function recognizeSpeech({onResult,onError,onEnd,onStart,onProcessing}) {
  if(!navigator.mediaDevices?.getUserMedia || !window.MediaRecorder) {
    onError('Trình duyệt chưa hỗ trợ ghi âm. Hãy dùng Chrome hoặc Edge trên localhost/HTTPS.');
    return null;
  }
  let recorder,stream,timer,cancelled=false,stopping=false;
  const request=new AbortController();
  const release=()=>{clearTimeout(timer);stream?.getTracks().forEach(track=>track.stop());};
  const controls={
    stop(){stopping=true;if(recorder?.state==='recording')recorder.stop();},
    abort(){cancelled=true;request.abort();if(recorder?.state==='recording')recorder.stop();release();},
  };
  (async()=>{
    try {
      onStart('Đang mở micro…');
      stream=await navigator.mediaDevices.getUserMedia({audio:true});
      if(cancelled || stopping){release();if(!cancelled)onEnd();return;}
      const mime=['audio/webm;codecs=opus','audio/ogg;codecs=opus','audio/mp4'].find(type=>MediaRecorder.isTypeSupported(type));
      recorder=new MediaRecorder(stream,mime?{mimeType:mime}:undefined);
      const chunks=[];
      recorder.ondataavailable=event=>{if(event.data.size)chunks.push(event.data);};
      recorder.onerror=()=>{release();if(!cancelled){onError('Ghi âm bị gián đoạn. Hãy thử lại.');onEnd();}};
      recorder.onstop=async()=>{
        release();
        if(cancelled)return;
        try {
          const blob=new Blob(chunks,{type:recorder.mimeType || 'audio/webm'});
          if(!blob.size)throw new Error('Chưa ghi được âm thanh. Hãy thử lại.');
          if(blob.size>5*1024*1024)throw new Error('Âm thanh tối đa 5 MB.');
          onProcessing('Đang nhận dạng bằng Whisper trên máy local…');
          const body=new FormData();body.append('audio',blob,'voice');
          const result=await api('/search/voice',{method:'POST',body,timeout:180000,signal:request.signal});
          if(!cancelled)onResult(result.text);
        } catch(error){if(!cancelled)onError(error.message);}
        finally {if(!cancelled)onEnd();}
      };
      recorder.start();
      onStart('Đang nghe. Nói tên sản phẩm rồi bấm micro để dừng (tự dừng sau 8 giây). Âm thanh chỉ xử lý trên máy local.');
      timer=setTimeout(()=>controls.stop(),8000);
    } catch(error) {
      release();
      if(!cancelled){onError(error.name==='NotAllowedError'?'Bạn chưa cho phép micro. Hãy cấp quyền rồi thử lại.':'Không mở được micro. Kiểm tra thiết bị và thử lại.');onEnd();}
    }
  })();
  return controls;
}
