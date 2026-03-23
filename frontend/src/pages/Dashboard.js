import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Beer, Plus, Minus, CreditCard, Smartphone, ShoppingCart, History, Settings, LogOut, AlertTriangle, User } from 'lucide-react';
import { toast } from 'sonner';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Dashboard = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { user, logout, isAdmin, checkAuth } = useAuth();
  const currentUser = location.state?.user || user;

  const [products, setProducts] = useState([]);
  const [quantities, setQuantities] = useState({});
  const [showOrderDialog, setShowOrderDialog] = useState(false);
  const [paymentMethod, setPaymentMethod] = useState('credit');
  const [mpesaCode, setMpesaCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [creditBalance, setCreditBalance] = useState(currentUser?.credit_balance || 10000);

  useEffect(() => {
    fetchProducts();
    fetchCreditBalance();
  }, []);

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API}/products`, { withCredentials: true });
      setProducts(response.data);
      // Initialize quantities
      const initialQuantities = {};
      response.data.forEach(p => initialQuantities[p.product_id] = 0);
      setQuantities(initialQuantities);
    } catch (error) {
      toast.error('Failed to load products');
    }
  };

  const fetchCreditBalance = async () => {
    try {
      const response = await axios.get(`${API}/users/credit-balance`, { withCredentials: true });
      setCreditBalance(response.data.credit_balance);
    } catch (error) {
      console.error('Failed to fetch credit balance');
    }
  };

  const updateQuantity = (productId, delta) => {
    setQuantities(prev => {
      const newQty = Math.max(0, Math.min(5, (prev[productId] || 0) + delta));
      const totalQty = Object.entries(prev).reduce((sum, [id, qty]) => {
        if (id === productId) return sum + newQty;
        return sum + qty;
      }, 0);
      
      if (totalQty > 5) {
        toast.error('Maximum 5 bottles per order');
        return prev;
      }
      
      return { ...prev, [productId]: newQty };
    });
  };

  const totalQuantity = Object.values(quantities).reduce((sum, qty) => sum + qty, 0);
  const totalAmount = products.reduce((sum, p) => sum + (quantities[p.product_id] || 0) * p.price, 0);

  const handleOrder = () => {
    if (totalQuantity === 0) {
      toast.error('Please select at least one item');
      return;
    }
    setShowOrderDialog(true);
  };

  const submitOrder = async () => {
    if (paymentMethod === 'mpesa' && (!mpesaCode || mpesaCode.length < 5)) {
      toast.error('Please enter a valid M-Pesa transaction code');
      return;
    }

    if (paymentMethod === 'credit' && creditBalance < totalAmount) {
      toast.error('Insufficient credit balance');
      return;
    }

    setLoading(true);
    try {
      const items = products
        .filter(p => quantities[p.product_id] > 0)
        .map(p => ({
          product_name: p.name,
          quantity: quantities[p.product_id],
          price: p.price
        }));

      await axios.post(
        `${API}/orders`,
        {
          items,
          payment_method: paymentMethod,
          mpesa_code: paymentMethod === 'mpesa' ? mpesaCode : null
        },
        { withCredentials: true }
      );

      toast.success('Order placed successfully!');
      setShowOrderDialog(false);
      
      // Reset quantities
      const resetQuantities = {};
      products.forEach(p => resetQuantities[p.product_id] = 0);
      setQuantities(resetQuantities);
      setMpesaCode('');
      
      // Refresh credit balance
      fetchCreditBalance();
      checkAuth();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to place order');
    } finally {
      setLoading(false);
    }
  };

  const usedCredit = 10000 - creditBalance;
  const showWarning = usedCredit > 5000;

  if (!currentUser) {
    return null;
  }

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="bg-hh-green border-b-2 border-black p-4 sticky top-0 z-40">
        <div className="max-w-md mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
              <Beer className="w-6 h-6 text-hh-green" />
            </div>
            <h1 className="font-display text-xl font-bold uppercase tracking-tight text-black">
              HH Jaba
            </h1>
          </div>
          <div className="flex items-center gap-2">
            {isAdmin && (
              <Button
                data-testid="admin-btn"
                variant="outline"
                size="sm"
                onClick={() => navigate('/admin')}
                className="border-2 border-black font-display uppercase text-xs"
              >
                <Settings className="w-4 h-4" />
              </Button>
            )}
            <Button
              data-testid="logout-btn"
              variant="outline"
              size="sm"
              onClick={logout}
              className="border-2 border-black font-display uppercase text-xs"
            >
              <LogOut className="w-4 h-4" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4 pb-32">
        <div className="max-w-md mx-auto space-y-6">
          {/* User Info */}
          <div className="flex items-center gap-3 p-3 bg-gray-100 border-2 border-black rounded-lg">
            <div className="w-10 h-10 bg-hh-green rounded-full flex items-center justify-center border-2 border-black">
              <User className="w-5 h-5 text-black" />
            </div>
            <div className="flex-1">
              <p className="font-display uppercase text-sm">{currentUser?.name}</p>
              <p className="text-xs text-gray-600">{currentUser?.email}</p>
            </div>
          </div>

          {/* Credit Balance Card */}
          <div className={`p-4 border-2 border-black shadow-brutal rounded-lg ${showWarning ? 'bg-orange-50' : 'bg-hh-green/10'}`}>
            <div className="flex items-center justify-between mb-2">
              <span className="font-display uppercase text-sm text-gray-600">Credit Balance</span>
              <CreditCard className="w-5 h-5 text-gray-600" />
            </div>
            <p className="font-display text-3xl font-bold text-black">
              KES {creditBalance.toLocaleString('en-KE', { minimumFractionDigits: 2 })}
            </p>
            {showWarning && (
              <div className="mt-3 flex items-start gap-2 text-orange-700 text-sm">
                <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
                <p>Please clear balance by the 5th of next month to avoid 16% VAT penalty</p>
              </div>
            )}
          </div>

          {/* Quick Actions */}
          <div className="flex gap-3">
            <Button
              data-testid="orders-history-btn"
              variant="outline"
              onClick={() => navigate('/orders')}
              className="flex-1 h-12 border-2 border-black font-display uppercase text-sm shadow-brutal-sm btn-brutal"
            >
              <History className="w-4 h-4 mr-2" />
              Orders
            </Button>
          </div>

          {/* Flavors Section */}
          <div>
            <h2 className="font-display text-xl uppercase tracking-tight mb-4">
              Choose Your Flavors
            </h2>
            <p className="text-sm text-gray-600 mb-4">KES 500 per bottle • Max 5 per order</p>

            <div className="grid grid-cols-2 gap-3">
              {products.map((product) => (
                <div
                  key={product.product_id}
                  data-testid={`product-card-${product.product_id}`}
                  className="border-2 border-black rounded-lg overflow-hidden shadow-brutal-sm bg-white"
                >
                  <div 
                    className="h-28 relative overflow-hidden"
                    style={{ backgroundColor: product.color + '15' }}
                  >
                    {product.image_url ? (
                      <img 
                        src={product.image_url} 
                        alt={product.name}
                        className="w-full h-full object-cover"
                      />
                    ) : (
                      <div className="w-full h-full flex items-center justify-center">
                        <div 
                          className="w-12 h-12 rounded-full border-2 border-black"
                          style={{ backgroundColor: product.color }}
                        />
                      </div>
                    )}
                    <div 
                      className="absolute top-2 left-2 w-4 h-4 rounded-full border-2 border-black shadow-sm"
                      style={{ backgroundColor: product.color }}
                    />
                    {product.stock < 10 && (
                      <span className="absolute top-2 right-2 text-xs bg-red-500 text-white px-1 rounded">
                        Low
                      </span>
                    )}
                  </div>
                  <div className="p-3">
                    <p className="font-display text-xs uppercase tracking-tight leading-tight mb-1">
                      {product.name.replace('Happy Hour Jaba - ', '')}
                    </p>
                    <p className="text-xs text-gray-500 mb-2">KES 500</p>
                    
                    {/* Quantity Selector */}
                    <div className="flex items-center justify-between">
                      <Button
                        data-testid={`decrease-${product.product_id}`}
                        variant="outline"
                        size="sm"
                        onClick={() => updateQuantity(product.product_id, -1)}
                        disabled={quantities[product.product_id] === 0}
                        className="w-8 h-8 p-0 border-2 border-black"
                      >
                        <Minus className="w-3 h-3" />
                      </Button>
                      <span className="font-display text-lg font-bold w-8 text-center">
                        {quantities[product.product_id] || 0}
                      </span>
                      <Button
                        data-testid={`increase-${product.product_id}`}
                        variant="outline"
                        size="sm"
                        onClick={() => updateQuantity(product.product_id, 1)}
                        disabled={product.stock === 0 || totalQuantity >= 5}
                        className="w-8 h-8 p-0 border-2 border-black"
                      >
                        <Plus className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </main>

      {/* Fixed Order Button */}
      <div className="fixed bottom-0 left-0 right-0 p-4 bg-white border-t-2 border-black">
        <div className="max-w-md mx-auto">
          <Button
            data-testid="place-order-btn"
            onClick={handleOrder}
            disabled={totalQuantity === 0}
            className="w-full h-14 bg-hh-green text-black hover:bg-green-600 text-lg font-display uppercase tracking-wide border-2 border-black shadow-brutal btn-brutal transition-all disabled:opacity-50"
          >
            <ShoppingCart className="mr-2 w-5 h-5" />
            Order {totalQuantity > 0 ? `(${totalQuantity})` : ''} • KES {totalAmount.toLocaleString()}
          </Button>
        </div>
      </div>

      {/* Order Dialog */}
      <Dialog open={showOrderDialog} onOpenChange={setShowOrderDialog}>
        <DialogContent className="max-w-md border-2 border-black shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Complete Order</DialogTitle>
            <DialogDescription>Choose your payment method</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Order Summary */}
            <div className="p-3 bg-gray-100 rounded-lg border-2 border-black">
              <p className="font-display uppercase text-sm mb-2">Order Summary</p>
              {products.filter(p => quantities[p.product_id] > 0).map(p => (
                <div key={p.product_id} className="flex justify-between text-sm">
                  <span>{p.name.replace('Happy Hour Jaba - ', '')} × {quantities[p.product_id]}</span>
                  <span>KES {(quantities[p.product_id] * p.price).toLocaleString()}</span>
                </div>
              ))}
              <div className="border-t border-gray-300 mt-2 pt-2 flex justify-between font-bold">
                <span>Total</span>
                <span>KES {totalAmount.toLocaleString()}</span>
              </div>
            </div>

            {/* Payment Tabs */}
            <Tabs value={paymentMethod} onValueChange={setPaymentMethod}>
              <TabsList className="grid w-full grid-cols-2 border-2 border-black">
                <TabsTrigger 
                  data-testid="credit-tab"
                  value="credit"
                  className="font-display uppercase data-[state=active]:bg-hh-green data-[state=active]:text-black"
                >
                  <CreditCard className="w-4 h-4 mr-2" />
                  Credit
                </TabsTrigger>
                <TabsTrigger 
                  data-testid="mpesa-tab"
                  value="mpesa"
                  className="font-display uppercase data-[state=active]:bg-hh-green data-[state=active]:text-black"
                >
                  <Smartphone className="w-4 h-4 mr-2" />
                  M-Pesa
                </TabsTrigger>
              </TabsList>

              <TabsContent value="credit" className="mt-4">
                <div className="p-3 bg-hh-green/10 rounded-lg border-2 border-hh-green">
                  <p className="text-sm mb-1">Available Balance:</p>
                  <p className="font-display text-2xl font-bold">KES {creditBalance.toLocaleString()}</p>
                  {creditBalance < totalAmount && (
                    <p className="text-red-600 text-sm mt-2">Insufficient balance</p>
                  )}
                </div>
              </TabsContent>

              <TabsContent value="mpesa" className="mt-4 space-y-3">
                <div className="p-3 bg-green-50 rounded-lg border-2 border-green-600">
                  <p className="text-sm font-bold">Pay to: Pam's Airtel</p>
                  <p className="font-display text-xl">0733 8780020</p>
                  <p className="text-sm mt-1">Amount: KES {totalAmount.toLocaleString()}</p>
                </div>
                
                <div>
                  <Label htmlFor="mpesa-code" className="font-display uppercase text-sm">
                    M-Pesa Transaction Code
                  </Label>
                  <Input
                    data-testid="mpesa-code-input"
                    id="mpesa-code"
                    placeholder="e.g., ABC123XYZ"
                    value={mpesaCode}
                    onChange={(e) => setMpesaCode(e.target.value.toUpperCase())}
                    className="mt-1 h-12 border-2 border-black uppercase"
                  />
                </div>
              </TabsContent>
            </Tabs>

            {/* Submit Button */}
            <Button
              data-testid="confirm-order-btn"
              onClick={submitOrder}
              disabled={loading || (paymentMethod === 'credit' && creditBalance < totalAmount)}
              className="w-full h-14 bg-hh-green text-black hover:bg-green-600 text-lg font-display uppercase tracking-wide border-2 border-black shadow-brutal btn-brutal disabled:opacity-50"
            >
              {loading ? 'Processing...' : 'Confirm Order'}
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default Dashboard;
