import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useLocation } from 'react-router-dom';
import { Button } from '../components/ui/button';
import { Beer, ArrowRight, AlertCircle } from 'lucide-react';
import { Alert, AlertDescription } from '../components/ui/alert';

const Landing = () => {
  const { login } = useAuth();
  const location = useLocation();
  const errorMessage = location.state?.error;

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="bg-hh-green border-b-2 border-black p-4">
        <div className="max-w-md mx-auto flex items-center gap-3">
          <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
            <Beer className="w-6 h-6 text-hh-green" />
          </div>
          <h1 className="font-display text-2xl font-bold uppercase tracking-tight text-black">
            HH Jaba
          </h1>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex flex-col items-center justify-center p-6">
        <div className="w-full max-w-md">
          {/* Hero Image */}
          <div className="relative mb-8">
            <img
              src="https://customer-assets.emergentagent.com/job_jaba-admin-hub/artifacts/f9epea1o_5%20tastes.jpg"
              alt="Happy Hour Jaba - All Flavors"
              className="w-full h-72 object-cover border-2 border-black shadow-brutal rounded-lg"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-black/60 to-transparent rounded-lg flex items-end p-4">
              <p className="text-white font-display text-xl uppercase">
                5DM Staff Portal
              </p>
            </div>
          </div>

          {/* Error Alert */}
          {errorMessage && (
            <Alert variant="destructive" className="mb-6 border-2 border-black shadow-brutal-sm">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{errorMessage}</AlertDescription>
            </Alert>
          )}

          {/* Welcome Text */}
          <div className="text-center mb-8">
            <h2 className="font-display text-3xl font-bold uppercase tracking-tight mb-2">
              Happy Hour Jaba
            </h2>
            <p className="text-gray-600 font-body">
              Order your favorite flavored beers with ease. 
              Credit or M-Pesa – your choice.
            </p>
          </div>

          {/* Features - All 6 Flavors */}
          <div className="grid grid-cols-3 gap-2 mb-8">
            <div className="bg-flavor-tamarind/10 border-2 border-flavor-tamarind p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-tamarind rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Tamarind</span>
            </div>
            <div className="bg-flavor-watermelon/10 border-2 border-flavor-watermelon p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-watermelon rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Watermelon</span>
            </div>
            <div className="bg-flavor-beetroot/10 border-2 border-flavor-beetroot p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-beetroot rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Beetroot</span>
            </div>
            <div className="bg-flavor-pineapple/10 border-2 border-flavor-pineapple p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-pineapple rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Pineapple</span>
            </div>
            <div className="bg-flavor-hibiscus/10 border-2 border-flavor-hibiscus p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-flavor-hibiscus rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Hibiscus</span>
            </div>
            <div className="bg-purple-500/10 border-2 border-purple-500 p-2 rounded-lg text-center">
              <div className="w-3 h-3 bg-purple-500 rounded-full mx-auto mb-1"></div>
              <span className="text-xs font-display uppercase">Mixed Fruit</span>
            </div>
          </div>

          {/* Login Button */}
          <Button
            data-testid="login-btn"
            onClick={login}
            className="w-full h-14 bg-hh-green text-black hover:bg-green-600 text-lg font-display uppercase tracking-wide border-2 border-black shadow-brutal btn-brutal transition-all"
          >
            Sign in with Google
            <ArrowRight className="ml-2 w-5 h-5" />
          </Button>

          <p className="text-center text-sm text-gray-500 mt-4">
            Only @5dm.africa emails allowed
          </p>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-black text-white p-4 text-center">
        <p className="text-sm">© 2026 5DM Africa. Happy Hour Jaba.</p>
      </footer>
    </div>
  );
};

export default Landing;
