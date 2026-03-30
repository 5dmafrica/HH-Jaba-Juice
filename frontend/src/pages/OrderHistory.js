import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Badge } from '../components/ui/badge';
import { Beer, ArrowLeft, Filter, Download, Mail, CreditCard, Smartphone, Check, Clock, X } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const OrderHistory = () => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filterPayment, setFilterPayment] = useState('all');
  const [filterStatus, setFilterStatus] = useState('all');

  const fetchOrders = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterPayment !== 'all') params.append('payment_method', filterPayment);
      if (filterStatus !== 'all') params.append('status', filterStatus);
      
      const response = await axios.get(`${API}/orders?${params.toString()}`, { withCredentials: true });
      setOrders(response.data);
    } catch (error) {
      toast.error('Failed to load orders');
    } finally {
      setLoading(false);
    }
  }, [filterPayment, filterStatus]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);



  const getStatusBadge = (status, verificationStatus) => {
    if (status === 'fulfilled' && verificationStatus === 'verified') {
      return <Badge className="bg-hh-green text-black border-2 border-black"><Check className="w-3 h-3 mr-1" />Fulfilled</Badge>;
    }
    if (status === 'pending') {
      return <Badge className="bg-yellow-400 text-black border-2 border-black"><Clock className="w-3 h-3 mr-1" />Pending</Badge>;
    }
    if (status === 'cancelled') {
      return <Badge className="bg-red-500 text-white border-2 border-black"><X className="w-3 h-3 mr-1" />Cancelled</Badge>;
    }
    return <Badge className="bg-gray-400 text-black border-2 border-black">{status}</Badge>;
  };

  const getPaymentIcon = (method) => {
    return method === 'credit' 
      ? <CreditCard className="w-4 h-4" />
      : <Smartphone className="w-4 h-4" />;
  };

  const totalPaid = orders.filter(o => o.status === 'fulfilled').reduce((sum, o) => sum + o.total_amount, 0);
  const totalPending = orders.filter(o => o.status === 'pending').reduce((sum, o) => sum + o.total_amount, 0);

  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* Header */}
      <header className="bg-hh-green border-b-2 border-black p-4 sticky top-0 z-40">
        <div className="max-w-md mx-auto flex items-center gap-3">
          <Button
            data-testid="back-btn"
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard')}
            className="p-2"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-3 flex-1">
            <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
              <Beer className="w-6 h-6 text-hh-green" />
            </div>
            <h1 className="font-display text-xl font-bold uppercase tracking-tight text-black">
              Order History
            </h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4">
        <div className="max-w-md mx-auto space-y-4">
          {/* Stats */}
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 bg-hh-green/10 border-2 border-black rounded-lg shadow-brutal-sm">
              <p className="text-xs font-display uppercase text-gray-600">Total Paid</p>
              <p className="font-display text-xl font-bold">KES {totalPaid.toLocaleString()}</p>
            </div>
            <div className="p-3 bg-yellow-50 border-2 border-black rounded-lg shadow-brutal-sm">
              <p className="text-xs font-display uppercase text-gray-600">Pending</p>
              <p className="font-display text-xl font-bold">KES {totalPending.toLocaleString()}</p>
            </div>
          </div>

          {/* Filters */}
          <div className="flex gap-2">
            <div className="flex-1">
              <Select value={filterPayment} onValueChange={setFilterPayment}>
                <SelectTrigger data-testid="filter-payment" className="border-2 border-black h-10">
                  <SelectValue placeholder="Payment" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Payments</SelectItem>
                  <SelectItem value="credit">Credit</SelectItem>
                  <SelectItem value="mpesa">M-Pesa</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div className="flex-1">
              <Select value={filterStatus} onValueChange={setFilterStatus}>
                <SelectTrigger data-testid="filter-status" className="border-2 border-black h-10">
                  <SelectValue placeholder="Status" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Status</SelectItem>
                  <SelectItem value="pending">Pending</SelectItem>
                  <SelectItem value="fulfilled">Fulfilled</SelectItem>
                  <SelectItem value="cancelled">Cancelled</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Orders List */}
          {loading ? (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-2 border-black border-t-hh-green rounded-full animate-spin mx-auto"></div>
            </div>
          ) : orders.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
              <Beer className="w-12 h-12 mx-auto text-gray-400 mb-3" />
              <p className="text-gray-500">No orders found</p>
            </div>
          ) : (
            <div className="space-y-3">
              {orders.map((order) => (
                <div
                  key={order.order_id}
                  data-testid={`order-card-${order.order_id}`}
                  className="p-4 border-2 border-black rounded-lg shadow-brutal-sm bg-white"
                >
                  <div className="flex items-start justify-between mb-2">
                    <div>
                      <p className="font-display text-sm font-bold">{order.order_id}</p>
                      <p className="text-xs text-gray-500">
                        {format(new Date(order.created_at), 'MMM dd, yyyy • HH:mm')}
                      </p>
                    </div>
                    {getStatusBadge(order.status, order.verification_status)}
                  </div>
                  
                  {/* Items */}
                  <div className="space-y-1 mb-3">
                    {order.items.map((item, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span>{item.product_name.replace('Happy Hour Jaba - ', '')} × {item.quantity}</span>
                        <span>KES {(item.quantity * item.price).toLocaleString()}</span>
                      </div>
                    ))}
                  </div>

                  <div className="flex items-center justify-between pt-2 border-t border-gray-200">
                    <div className="flex items-center gap-2">
                      {getPaymentIcon(order.payment_method)}
                      <span className="text-xs uppercase">{order.payment_method}</span>
                      {order.mpesa_code && (
                        <span className="text-xs text-gray-500">({order.mpesa_code})</span>
                      )}
                    </div>
                    <p className="font-display font-bold">KES {order.total_amount.toLocaleString()}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  );
};

export default OrderHistory;
