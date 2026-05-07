import { useEffect, useRef, useCallback, useState } from 'react';

interface UseWebSocketOptions {
  onAudioChunk?: (base64Data: string) => void;
  onInterrupted?: () => void;
  onUIEvent?: (view: string) => void;
  onOpen?: () => void;
  onClose?: () => void;
  onError?: (error: Event) => void;
}

export const useWebSocket = (url: string, options: UseWebSocketOptions) => {
  const ws = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const optionsRef = useRef(options);
  
  useEffect(() => {
    optionsRef.current = options;
  }, [options]);

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('[WS] Already connected');
      return;
    }
    
    console.log('[WS] Connecting to:', url);
    const socket = new WebSocket(url);
    socket.binaryType = 'arraybuffer';
    ws.current = socket;

    socket.onopen = () => {
      console.log('[WS] Connected successfully');
      setIsConnected(true);
      optionsRef.current.onOpen?.();
    };

    socket.onmessage = (event) => {
      if (typeof event.data === 'string') {
        try {
          const data = JSON.parse(event.data);
          
          if (data.type === 'interrupted') {
            optionsRef.current.onInterrupted?.();
          } else if (data.type === 'ui_event') {
            console.log('[WS] UI Event received:', data.view);
            optionsRef.current.onUIEvent?.(data.view);
          } else if (data.type === 'error') {
            console.error('[WS] Server error:', data.message);
          }
        } catch (e) {
          console.error('[WS] Error parsing JSON message', e);
        }
      } else if (event.data instanceof ArrayBuffer) {
        // Handle binary audio chunk directly
        const base64 = btoa(
          new Uint8Array(event.data).reduce((data, byte) => data + String.fromCharCode(byte), '')
        );
        optionsRef.current.onAudioChunk?.(base64);
      }
    };

    socket.onclose = (event) => {
      console.log('[WS] Disconnected:', event.code, event.reason);
      setIsConnected(false);
      optionsRef.current.onClose?.();
    };

    socket.onerror = (error) => {
      console.error('[WS] Error:', error);
      optionsRef.current.onError?.(error);
    };
  }, [url]);

  const disconnect = useCallback(() => {
    ws.current?.close();
  }, []);

  const sendAudio = useCallback((base64Data: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify({
        type: 'audio',
        data: base64Data
      }));
    }
  }, []);

  const sendUIReady = useCallback((node: string) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      console.log('[WS] Sending ui_ready for:', node);
      ws.current.send(JSON.stringify({
        type: 'ui_ready',
        node: node
      }));
    }
  }, []);

  useEffect(() => {
    return () => {
      ws.current?.close();
    };
  }, []);

  return { connect, disconnect, isConnected, sendAudio, sendUIReady };
};
