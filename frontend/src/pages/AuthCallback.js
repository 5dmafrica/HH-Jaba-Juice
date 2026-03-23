import React, { useEffect, useRef } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { Beer } from 'lucide-react';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const AuthCallback = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { updateUser } = useAuth();
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Use useRef to prevent double processing in StrictMode
    if (hasProcessed.current) return;
    hasProcessed.current = true;

    const processAuth = async () => {
      try {
        // Extract session_id from URL hash
        const hash = location.hash;
        const sessionIdMatch = hash.match(/session_id=([^&]+)/);
        
        if (!sessionIdMatch) {
          navigate('/', { replace: true });
          return;
        }

        const sessionId = sessionIdMatch[1];

        // Exchange session_id for session_token
        const response = await axios.post(
          `${API}/auth/session`,
          { session_id: sessionId },
          { withCredentials: true }
        );

        const userData = response.data.user;
        updateUser(userData);

        // Check if profile setup is needed
        if (!userData.phone || !userData.accepted_terms) {
          navigate('/profile-setup', { replace: true, state: { user: userData } });
        } else {
          navigate('/dashboard', { replace: true, state: { user: userData } });
        }
      } catch (error) {
        console.error('Auth callback error:', error);
        const errorMessage = error.response?.data?.detail || 'Authentication failed';
        navigate('/', { replace: true, state: { error: errorMessage } });
      }
    };

    processAuth();
  }, [location, navigate, updateUser]);

  return (
    <div className="min-h-screen bg-white flex items-center justify-center">
      <div className="text-center">
        <div className="w-16 h-16 bg-hh-green border-2 border-black shadow-brutal rounded-lg flex items-center justify-center mx-auto mb-4 animate-pulse">
          <Beer className="w-8 h-8 text-black" />
        </div>
        <p className="font-display text-xl uppercase tracking-wide">Authenticating...</p>
      </div>
    </div>
  );
};

export default AuthCallback;
