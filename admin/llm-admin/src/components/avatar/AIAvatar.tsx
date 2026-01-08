import React, { useEffect, useRef, useState } from 'react';

interface AIAvatarProps {
  isTalking: boolean;
  textToSpeak?: string;
  onSpeechStart?: () => void;
  onSpeechEnd?: () => void;
}

export default function AIAvatar({ isTalking, textToSpeak, onSpeechStart, onSpeechEnd }: AIAvatarProps) {
  const videoContainerRef = useRef<HTMLDivElement>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const [status, setStatus] = useState<string>('Initializing...');
  const synthesizerRef = useRef<any>(null);
  const peerConnectionRef = useRef<RTCPeerConnection | null>(null);
  const [SpeechSDK, setSpeechSDK] = useState<any>(null);
  const [isReady, setIsReady] = useState(false);
  const lastSpokenTextRef = useRef<string | undefined>(undefined);
  const isInitializingRef = useRef(false);

  useEffect(() => {
    import('microsoft-cognitiveservices-speech-sdk').then((module) => {
      setSpeechSDK(module);
    }).catch(err => {
    });
  }, []);

  useEffect(() => {
    if (!SpeechSDK || synthesizerRef.current || isInitializingRef.current) return;

    let aborted = false;

    const initAvatar = async () => {
      isInitializingRef.current = true;
      
      try {
        setStatus('Initializing Avatar...');
        
        const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

        // 1. Get Tokens
        const [avatarTokenRes, speechTokenRes] = await Promise.all([
            fetch(`${API_URL}/api/azure-avatar-token`),
            fetch(`${API_URL}/api/speech-token`)
        ]);

        if (aborted) return;

        if (!avatarTokenRes.ok || !speechTokenRes.ok) {
            throw new Error(`Failed to fetch tokens: ${avatarTokenRes.status} ${speechTokenRes.status}`);
        }

        const avatarTokenData = await avatarTokenRes.json();
        const speechTokenData = await speechTokenRes.json();

        // 2. Setup WebRTC
        // Follow the working sample's pattern: Use the first URL from the list
        const iceServerUrl = avatarTokenData.Urls[0];
        console.log(`Using ICE Server URL: ${iceServerUrl}`);
        const iceServers = [
            {
                urls: [iceServerUrl], 
                username: avatarTokenData.Username,
                credential: avatarTokenData.Password
            }
        ];

        const peerConnection = new RTCPeerConnection({ iceServers });
        peerConnectionRef.current = peerConnection;

        // Add transceivers to ensure SDP contains audio/video sections
        peerConnection.addTransceiver('video', { direction: 'sendrecv' });
        peerConnection.addTransceiver('audio', { direction: 'sendrecv' });
        
        // Data Channel is required for Azure Avatar
        peerConnection.createDataChannel("eventChannel");

        peerConnection.oniceconnectionstatechange = () => {
            if (peerConnection.iceConnectionState === 'connected') {
                console.log("ICE Connected! Media should flow.");
            }
        };

        peerConnection.onconnectionstatechange = () => {
            console.log(`Connection State: ${peerConnection.connectionState}`);
        };

        peerConnection.onicecandidate = (event) => {
             if (event.candidate) {
                 console.log(`Local ICE Candidate: ${event.candidate.candidate.substring(0, 50)}...`);
             }
        };

        peerConnection.ontrack = (event) => {
            if (event.track.kind === 'video') {
                // Create video element manually to match chat.js behavior
                const video = document.createElement('video');
                video.srcObject = event.streams[0];
                video.autoplay = true;
                video.playsInline = true;
                video.style.width = '100%';
                video.style.height = '100%';
                video.style.objectFit = 'contain'; // Changed from cover to contain to prevent zooming/cropping
                video.id = 'videoPlayer';

                if (videoContainerRef.current) {
                    videoContainerRef.current.innerHTML = '';
                    videoContainerRef.current.appendChild(video);
                    videoRef.current = video;
                }

            }
        };

        // 3. Setup Avatar Synthesizer
        const speechConfig = SpeechSDK.SpeechConfig.fromAuthorizationToken(
            speechTokenData.token, 
            speechTokenData.region
        );

        // https://learn.microsoft.com/ko-kr/azure/ai-services/speech-service/language-support?tabs=tts
        // speechConfig.speechSynthesisVoiceName = "en-US-AvaMultilingualNeural"; 
        speechConfig.speechSynthesisVoiceName = "en-US-AndrewMultilingualNeural";
        
        // Configure Avatar
        // Match the working sample: No background color, no video format crop
        // Video Avatar example: "lisa", "casual-sitting"
        // const avatarConfig = new SpeechSDK.AvatarConfig("lisa", "casual-sitting");

        // Photo Avatar example: "Isabella", "" (style is empty for photo avatars)
        // IMPORTANT: For Photo Avatar, you MUST set photoAvatarBaseModel to "vasa-1"
        const avatarConfig = new SpeechSDK.AvatarConfig("Matteo", ""); 
        avatarConfig.photoAvatarBaseModel = "vasa-1"; // Required for photo avatars
        avatarConfig.customized = false; 

        // Set video format to 1920x1080
        avatarConfig.videoFormat = new SpeechSDK.AvatarVideoFormat();
        avatarConfig.videoFormat.width = 1920;
        avatarConfig.videoFormat.height = 1080;
        
        
        const synthesizer = new SpeechSDK.AvatarSynthesizer(speechConfig, avatarConfig);
        synthesizerRef.current = synthesizer;

        // synthesizer.avatarEventReceived = (s: any, e: any) => {
        //     addDebugLog(`Avatar event: ${e.description}`);
        // };

        // Start Avatar
        // addDebugLog("Starting avatar async...");
        if (aborted) {
            synthesizer.close();
            peerConnection.close();
            return;
        }

        const result = await synthesizer.startAvatarAsync(peerConnection);
        
        if (aborted) {
            synthesizer.close();
            peerConnection.close();
            return;
        }

        if (result.reason === SpeechSDK.ResultReason.SynthesizingAudioCompleted) {
            setStatus('Ready');
            setIsReady(true);
        } else {
            setStatus(`Failed to start avatar: ${result.errorDetails}`);
            isInitializingRef.current = false; // Allow retry if failed
        }

      } catch (error: any) {
        if (aborted) return;
        console.error("Avatar init failed", error);
        setStatus(`Error: ${error.message}`);
        isInitializingRef.current = false; // Allow retry if failed
      }
    };

    initAvatar();

    return () => {
        aborted = true;
        isInitializingRef.current = false; // Reset initialization flag on unmount
        if (synthesizerRef.current) {
            synthesizerRef.current.close();
            synthesizerRef.current = null;
        }
        if (peerConnectionRef.current) {
            peerConnectionRef.current.close();
            peerConnectionRef.current = null;
        }
        if (videoContainerRef.current) {
            videoContainerRef.current.innerHTML = '';
        }
        videoRef.current = null;
    };
  }, [SpeechSDK]);

  // Handle Text to Speak
  useEffect(() => {
    if (isReady && synthesizerRef.current && textToSpeak && textToSpeak !== lastSpokenTextRef.current) {
        lastSpokenTextRef.current = textToSpeak;
        
        const speak = async () => {
            if (onSpeechStart) onSpeechStart();
            try {
                const result = await synthesizerRef.current.speakTextAsync(textToSpeak);
            } catch (e: any) {
                console.error("Speak error", e);
            } finally {
                if (onSpeechEnd) onSpeechEnd();
            }
        };
        speak();
    }
  }, [isReady, textToSpeak, onSpeechStart, onSpeechEnd]);

  return (
    <div className="w-full h-full flex items-center justify-center bg-gray-100 rounded-lg shadow-lg border border-gray-200 overflow-hidden relative">
      <div className="relative w-full h-full min-h-[400px] flex items-center justify-center overflow-hidden bg-gray-900">
        
        <div
          ref={videoContainerRef}
          className="w-full h-full flex items-center justify-center"
        />

        {/* Overlay to make it look more like a UI */}
        <div className="absolute inset-0 bg-gradient-to-t from-black/30 to-transparent pointer-events-none"></div>

      </div>
      
      <div className="absolute bottom-6 left-0 right-0 text-center pointer-events-none z-20">
        <div className={`inline-block px-4 py-2 rounded-full bg-white/90 backdrop-blur-sm shadow-sm transition-all duration-300 transform ${isTalking ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-2'}`}>
          <p className="text-sm text-indigo-600 font-bold flex items-center gap-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-indigo-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-indigo-500"></span>
            </span>
            질문하는 중...
          </p>
        </div>
      </div>
    </div>
  );
}
