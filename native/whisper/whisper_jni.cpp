#include <jni.h>
#include <whisper.h>
#include <atomic>
#include <memory>
#include <string>
#include <exception>
#include <stdexcept>

static std::atomic<bool> cancelled{false};
static std::atomic<int> percent{0};
static void fail(JNIEnv *env,const char *type,const char *message){env->ThrowNew(env->FindClass(type),message);}
extern "C" JNIEXPORT void JNICALL Java_chat_oldy_WhisperSpeech_abort(JNIEnv*,jclass){cancelled=true;}
extern "C" JNIEXPORT jint JNICALL Java_chat_oldy_WhisperSpeech_progress(JNIEnv*,jclass){return percent.load();}
extern "C" JNIEXPORT jstring JNICALL Java_chat_oldy_WhisperSpeech_transcribe(JNIEnv *env,jclass,jstring model,jfloatArray samples,jstring language,jint threads){
 cancelled=false;percent=0;
 const char *path=env->GetStringUTFChars(model,nullptr),*lang=env->GetStringUTFChars(language,nullptr);jfloat *audio=nullptr;
 try{whisper_log_set([](enum ggml_log_level,const char*,void*){},nullptr);auto cp=whisper_context_default_params();cp.use_gpu=false;std::unique_ptr<whisper_context,decltype(&whisper_free)> ctx(whisper_init_from_file_with_params(path,cp),whisper_free);if(!ctx)throw std::runtime_error("Cannot open speech model");
  auto params=whisper_full_default_params(WHISPER_SAMPLING_BEAM_SEARCH);params.beam_search.beam_size=3;params.n_threads=threads;params.language=lang;params.translate=false;params.no_context=true;params.no_timestamps=true;params.print_realtime=false;params.print_progress=false;params.print_timestamps=false;params.print_special=false;params.suppress_blank=true;params.temperature=0;params.temperature_inc=0;
  params.abort_callback=[](void*){return cancelled.load();};params.abort_callback_user_data=nullptr;
  params.progress_callback=[](whisper_context*,whisper_state*,int p,void*){percent=p;};params.progress_callback_user_data=nullptr;
  audio=env->GetFloatArrayElements(samples,nullptr);if(!audio)throw std::runtime_error("Not enough memory");int result=whisper_full(ctx.get(),params,audio,env->GetArrayLength(samples));std::string text;
  if(!cancelled&&result==0)for(int i=0;i<whisper_full_n_segments(ctx.get());i++)if(whisper_full_get_segment_no_speech_prob(ctx.get(),i)<0.8f)text+=whisper_full_get_segment_text(ctx.get(),i);
  env->ReleaseFloatArrayElements(samples,audio,JNI_ABORT);audio=nullptr;env->ReleaseStringUTFChars(model,path);env->ReleaseStringUTFChars(language,lang);
  if(cancelled){fail(env,"java/util/concurrent/CancellationException","Transcription cancelled");return nullptr;}if(result!=0){fail(env,"java/io/IOException","Speech recognition failed");return nullptr;}return env->NewStringUTF(text.c_str());
 }catch(const std::exception &){if(audio)env->ReleaseFloatArrayElements(samples,audio,JNI_ABORT);env->ReleaseStringUTFChars(model,path);env->ReleaseStringUTFChars(language,lang);fail(env,"java/io/IOException","Unable to run local speech recognition");return nullptr;}
}
