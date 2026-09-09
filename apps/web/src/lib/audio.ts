/**
 * Audio Manager for F.R.I.D.A.Y. Voice Playback.
 * Controls HTML5 Web Audio decoding, playback state, and stop triggers.
 */

let activeAudio: HTMLAudioElement | null = null;
let speakingListeners: Array<(isSpeaking: boolean) => void> = [];

export function subscribeSpeaking(callback: (isSpeaking: boolean) => void): () => void {
  speakingListeners.push(callback);
  return () => {
    speakingListeners = speakingListeners.filter((cb) => cb !== callback);
  };
}

function notifySpeaking(isSpeaking: boolean) {
  speakingListeners.forEach((cb) => cb(isSpeaking));
}

export function playBase64Audio(base64Mp3: string): Promise<void> {
  stopAudio();

  if (!base64Mp3) return Promise.resolve();

  return new Promise((resolve) => {
    try {
      activeAudio = new Audio(`data:audio/mp3;base64,${base64Mp3}`);
      notifySpeaking(true);

      activeAudio.onended = () => {
        notifySpeaking(false);
        activeAudio = null;
        resolve();
      };

      activeAudio.onerror = () => {
        notifySpeaking(false);
        activeAudio = null;
        resolve();
      };

      activeAudio.play().catch((err) => {
        console.warn("Autoplay was prevented by browser:", err);
        notifySpeaking(false);
        resolve();
      });
    } catch (e) {
      notifySpeaking(false);
      resolve();
    }
  });
}

export function stopAudio(): void {
  if (activeAudio) {
    activeAudio.pause();
    activeAudio.currentTime = 0;
    activeAudio = null;
  }
  notifySpeaking(false);
}

