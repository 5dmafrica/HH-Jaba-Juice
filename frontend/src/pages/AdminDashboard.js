import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '../components/ui/dialog';
import { Badge } from '../components/ui/badge';
import { Textarea } from '../components/ui/textarea';
import { 
  Beer, ArrowLeft, Clock, Package, Users, AlertTriangle, FileText,
  Check, X, Plus, Minus, RefreshCw, Mail, Smartphone, CreditCard, Receipt,
  Search, Gift, MessageSquare, Share2, Calendar
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import CreditInvoiceModule from '../components/CreditInvoiceModule';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const MONTHLY_CREDIT_LIMIT = 30000;

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user, isAdmin } = useAuth();
  const [activeTab, setActiveTab] = useState('pending');
  
  // Pending Orders State
  const [pendingOrders, setPendingOrders] = useState([]);
  const [pendingFilter, setPendingFilter] = useState('all');
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [cancellingOrder, setCancellingOrder] = useState(null);
  const [cancelReason, setCancelReason] = useState('');
  
  // Stock State
  const [products, setProducts] = useState([]);
  const [editingStock, setEditingStock] = useState(null);
  const [newStockValue, setNewStockValue] = useState(0);
  const [manufacturingDate, setManufacturingDate] = useState('');
  const [batchId, setBatchId] = useState('');
  
  // Reconciliation State
  const [reconciliation, setReconciliation] = useState([]);
  const [reconciliationSearch, setReconciliationSearch] = useState('');
  
  // Defaulters State
  const [defaulters, setDefaulters] = useState([]);
  const [defaultersSearch, setDefaultersSearch] = useState('');
  
  // Manual Invoice State
  const [manualInvoices, setManualInvoices] = useState([]);
  const [showInvoiceDialog, setShowInvoiceDialog] = useState(false);
  const [invoiceForm, setInvoiceForm] = useState({
    user_id: '',
    customer_name: '',
    amount: '',
    description: '',
    payment_method: 'credit',
    mpesa_code: '',
    product_name: '',
    quantity: ''
  });
  
  // Feedback State
  const [feedback, setFeedback] = useState([]);
  
  // Push Offer State
  const [showOfferDialog, setShowOfferDialog] = useState(false);
  const [offerTitle, setOfferTitle] = useState('');
  const [offerMessage, setOfferMessage] = useState('');
  
  // Auto Invoice Generation State
  const [showAutoInvoiceDialog, setShowAutoInvoiceDialog] = useState(false);
  const [autoInvoiceUserId, setAutoInvoiceUserId] = useState('');
  const [autoInvoiceStartDate, setAutoInvoiceStartDate] = useState('');
  const [autoInvoiceEndDate, setAutoInvoiceEndDate] = useState('');
  
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isAdmin) {
      navigate('/dashboard');
      return;
    }
    loadAllData();
  }, [isAdmin, navigate]);

  // Auto-refresh pending orders every 10 seconds when on pending tab
  useEffect(() => {
    if (activeTab === 'pending') {
      const interval = setInterval(() => {
        fetchPendingOrders();
      }, 10000); // Refresh every 10 seconds
      return () => clearInterval(interval);
    }
  }, [activeTab, pendingFilter]);

  const loadAllData = async () => {
    setLoading(true);
    try {
      await Promise.all([
        fetchPendingOrders(),
        fetchProducts(),
        fetchReconciliation(),
        fetchDefaulters(),
        fetchManualInvoices(),
        fetchUsers(),
        fetchFeedback()
      ]);
    } finally {
      setLoading(false);
    }
  };

  const fetchPendingOrders = async () => {
    try {
      const params = pendingFilter !== 'all' ? `?payment_method=${pendingFilter}` : '';
      const response = await axios.get(`${API}/admin/pending-orders${params}`, { withCredentials: true });
      setPendingOrders(response.data);
    } catch (error) {
      console.error('Failed to fetch pending orders');
    }
  };

  const fetchProducts = async () => {
    try {
      const response = await axios.get(`${API}/products/all`, { withCredentials: true });
      setProducts(response.data);
    } catch (error) {
      console.error('Failed to fetch products');
    }
  };

  const fetchReconciliation = async (search = '') => {
    try {
      const params = search ? `?search=${encodeURIComponent(search)}` : '';
      const response = await axios.get(`${API}/admin/reconciliation${params}`, { withCredentials: true });
      setReconciliation(response.data);
    } catch (error) {
      console.error('Failed to fetch reconciliation');
    }
  };

  const fetchDefaulters = async (search = '') => {
    try {
      const params = search ? `?search=${encodeURIComponent(search)}` : '';
      const response = await axios.get(`${API}/admin/defaulters${params}`, { withCredentials: true });
      setDefaulters(response.data);
    } catch (error) {
      console.error('Failed to fetch defaulters');
    }
  };

  const fetchManualInvoices = async () => {
    try {
      const response = await axios.get(`${API}/admin/manual-invoices`, { withCredentials: true });
      setManualInvoices(response.data);
    } catch (error) {
      console.error('Failed to fetch manual invoices');
    }
  };

  const fetchUsers = async () => {
    try {
      const response = await axios.get(`${API}/admin/users`, { withCredentials: true });
      setUsers(response.data);
    } catch (error) {
      console.error('Failed to fetch users');
    }
  };

  const fetchFeedback = async () => {
    try {
      const response = await axios.get(`${API}/admin/feedback`, { withCredentials: true });
      setFeedback(response.data);
    } catch (error) {
      console.error('Failed to fetch feedback');
    }
  };

  // Order Actions
  const fulfillOrder = async (orderId) => {
    try {
      await axios.post(`${API}/admin/orders/${orderId}/fulfill`, {}, { withCredentials: true });
      toast.success('Order fulfilled');
      fetchPendingOrders();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to fulfill order');
    }
  };

  const cancelOrder = async () => {
    if (!cancellingOrder || !cancelReason || cancelReason.length < 5) {
      toast.error('Please provide a reason (minimum 5 characters)');
      return;
    }
    try {
      await axios.post(`${API}/admin/orders/${cancellingOrder}/cancel`, { reason: cancelReason }, { withCredentials: true });
      toast.success('Order cancelled');
      setShowCancelDialog(false);
      setCancellingOrder(null);
      setCancelReason('');
      fetchPendingOrders();
      fetchReconciliation();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel order');
    }
  };

  const rejectOrder = async (orderId) => {
    // Open cancel dialog instead
    setCancellingOrder(orderId);
    setShowCancelDialog(true);
  };

  // Stock Actions - Now with production info and increment
  const updateStock = async () => {
    if (!editingStock) return;
    if (!manufacturingDate || !batchId) {
      toast.error('Manufacturing date and Batch ID are required');
      return;
    }
    try {
      await axios.put(
        `${API}/products/${editingStock}/stock`,
        { 
          stock: newStockValue,
          manufacturing_date: manufacturingDate,
          batch_id: batchId,
          increment: true  // Add to existing stock
        },
        { withCredentials: true }
      );
      toast.success(`Added ${newStockValue} units to stock`);
      setEditingStock(null);
      setNewStockValue(0);
      setManufacturingDate('');
      setBatchId('');
      fetchProducts();
    } catch (error) {
      toast.error('Failed to update stock');
    }
  };

  // Push Offer
  const sendPushOffer = async () => {
    if (!offerTitle || !offerMessage) {
      toast.error('Please fill in all fields');
      return;
    }
    try {
      await axios.post(`${API}/admin/notifications`, {
        title: offerTitle,
        message: offerMessage,
        notification_type: 'offer'
      }, { withCredentials: true });
      toast.success('Offer sent to all customers');
      setShowOfferDialog(false);
      setOfferTitle('');
      setOfferMessage('');
    } catch (error) {
      toast.error('Failed to send offer');
    }
  };

  // Auto Generate Invoice
  const autoGenerateInvoice = async () => {
    if (!autoInvoiceUserId || !autoInvoiceStartDate || !autoInvoiceEndDate) {
      toast.error('Please fill in all fields');
      return;
    }
    try {
      const response = await axios.post(`${API}/admin/auto-generate-invoice/${autoInvoiceUserId}`, {
        start_date: autoInvoiceStartDate,
        end_date: autoInvoiceEndDate
      }, { withCredentials: true });
      toast.success(`Invoice ${response.data.invoice_id} created`);
      setShowAutoInvoiceDialog(false);
      setAutoInvoiceUserId('');
      setAutoInvoiceStartDate('');
      setAutoInvoiceEndDate('');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate invoice');
    }
  };

  const deleteProduct = async (productId) => {
    if (!window.confirm('Are you sure you want to deactivate this product?')) return;
    try {
      await axios.delete(`${API}/products/${productId}`, { withCredentials: true });
      toast.success('Product deactivated');
      fetchProducts();
    } catch (error) {
      toast.error('Failed to deactivate product');
    }
  };

  // Manual Invoice Actions
  const createManualInvoice = async () => {
    try {
      await axios.post(`${API}/admin/manual-invoice`, {
        ...invoiceForm,
        amount: parseFloat(invoiceForm.amount) || 0,
        quantity: parseInt(invoiceForm.quantity) || null
      }, { withCredentials: true });
      toast.success('Invoice created');
      setShowInvoiceDialog(false);
      setInvoiceForm({
        user_id: '', customer_name: '', amount: '', description: '',
        payment_method: 'credit', mpesa_code: '', product_name: '', quantity: ''
      });
      fetchManualInvoices();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create invoice');
    }
  };

  const verifyInvoice = async (invoiceId) => {
    try {
      await axios.post(`${API}/admin/manual-invoices/${invoiceId}/verify`, {}, { withCredentials: true });
      toast.success('Invoice verified');
      fetchManualInvoices();
    } catch (error) {
      toast.error('Failed to verify invoice');
    }
  };

  const rejectInvoice = async (invoiceId) => {
    try {
      await axios.post(`${API}/admin/manual-invoices/${invoiceId}/reject`, {}, { withCredentials: true });
      toast.success('Invoice rejected');
      fetchManualInvoices();
    } catch (error) {
      toast.error('Failed to reject invoice');
    }
  };

  useEffect(() => {
    if (activeTab === 'pending') fetchPendingOrders();
  }, [pendingFilter]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-black text-white border-b-2 border-hh-green p-4 sticky top-0 z-40">
        <div className="max-w-6xl mx-auto flex items-center gap-3">
          <Button
            data-testid="back-to-dashboard"
            variant="ghost"
            size="sm"
            onClick={() => navigate('/dashboard')}
            className="text-white hover:bg-gray-800 p-2"
          >
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <div className="flex items-center gap-3 flex-1">
            <div className="w-10 h-10 bg-hh-green rounded-lg flex items-center justify-center">
              <Beer className="w-6 h-6 text-black" />
            </div>
            <div>
              <h1 className="font-display text-xl font-bold uppercase tracking-tight">
                Admin Dashboard
              </h1>
              <p className="text-xs text-gray-400">Happy Hour Jaba, Nairobi</p>
            </div>
          </div>
          <div className="flex gap-2">
            <Button
              data-testid="push-offer-btn"
              variant="ghost"
              size="sm"
              onClick={() => setShowOfferDialog(true)}
              className="text-white hover:bg-gray-800"
              title="Push Offer"
            >
              <Gift className="w-4 h-4" />
            </Button>
            <Button
              data-testid="auto-invoice-btn"
              variant="ghost"
              size="sm"
              onClick={() => setShowAutoInvoiceDialog(true)}
              className="text-white hover:bg-gray-800"
              title="Auto Generate Invoice"
            >
              <Calendar className="w-4 h-4" />
            </Button>
            <Button
              data-testid="refresh-data"
              variant="ghost"
              size="sm"
              onClick={loadAllData}
              className="text-white hover:bg-gray-800"
            >
              <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4">
        <div className="max-w-6xl mx-auto">
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-7 mb-6 border-2 border-black bg-white">
              <TabsTrigger 
                data-testid="tab-pending"
                value="pending" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <Clock className="w-4 h-4 mr-1 hidden sm:block" />
                Pending
                {pendingOrders.length > 0 && (
                  <Badge className="ml-1 bg-red-500 text-white text-xs">{pendingOrders.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger 
                data-testid="tab-stock"
                value="stock" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <Package className="w-4 h-4 mr-1 hidden sm:block" />
                Stock
              </TabsTrigger>
              <TabsTrigger 
                data-testid="tab-reconciliation"
                value="reconciliation" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <Users className="w-4 h-4 mr-1 hidden sm:block" />
                Reconcile
              </TabsTrigger>
              <TabsTrigger 
                data-testid="tab-defaulters"
                value="defaulters" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <AlertTriangle className="w-4 h-4 mr-1 hidden sm:block" />
                Defaulters
              </TabsTrigger>
              <TabsTrigger 
                data-testid="tab-credit-invoices"
                value="credit-invoices" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <Receipt className="w-4 h-4 mr-1 hidden sm:block" />
                Credit Inv
              </TabsTrigger>
              <TabsTrigger 
                data-testid="tab-invoices"
                value="invoices" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <FileText className="w-4 h-4 mr-1 hidden sm:block" />
                Manual
              </TabsTrigger>
              <TabsTrigger 
                data-testid="tab-feedback"
                value="feedback" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <MessageSquare className="w-4 h-4 mr-1 hidden sm:block" />
                Feedback
                {feedback.filter(f => f.status === 'new').length > 0 && (
                  <Badge className="ml-1 bg-purple-500 text-white text-xs">{feedback.filter(f => f.status === 'new').length}</Badge>
                )}
              </TabsTrigger>
            </TabsList>

            {/* PENDING ORDERS TAB */}
            <TabsContent value="pending" className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <div className="flex items-center gap-2">
                  <h2 className="font-display text-xl uppercase">Pending Orders</h2>
                  <Button
                    data-testid="refresh-pending-btn"
                    variant="outline"
                    size="sm"
                    onClick={fetchPendingOrders}
                    className="border-2 border-black"
                  >
                    <RefreshCw className="w-4 h-4" />
                  </Button>
                  <span className="text-xs text-gray-500">Auto-refreshes every 10s</span>
                </div>
                <Select value={pendingFilter} onValueChange={setPendingFilter}>
                  <SelectTrigger className="w-40 border-2 border-black">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All</SelectItem>
                    <SelectItem value="credit">Credit</SelectItem>
                    <SelectItem value="mpesa">M-Pesa</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {pendingOrders.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
                  <Check className="w-12 h-12 mx-auto text-hh-green mb-3" />
                  <p className="text-gray-500">No pending orders</p>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {pendingOrders.map((order) => (
                    <div
                      key={order.order_id}
                      data-testid={`pending-order-${order.order_id}`}
                      className="p-4 border-2 border-black rounded-lg shadow-brutal-sm bg-white"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="font-display font-bold">{order.order_id}</p>
                          <p className="text-sm text-gray-600">{order.user_name}</p>
                          <p className="text-xs text-gray-500">{order.user_phone}</p>
                        </div>
                        <Badge className={order.payment_method === 'credit' ? 'bg-blue-500' : 'bg-green-500'}>
                          {order.payment_method === 'credit' ? <CreditCard className="w-3 h-3 mr-1" /> : <Smartphone className="w-3 h-3 mr-1" />}
                          {order.payment_method}
                        </Badge>
                      </div>

                      <div className="space-y-1 mb-3 text-sm">
                        {order.items.map((item, idx) => (
                          <div key={idx} className="flex justify-between">
                            <span>{item.product_name.replace('Happy Hour Jaba - ', '')} × {item.quantity}</span>
                            <span>KES {(item.quantity * item.price).toLocaleString()}</span>
                          </div>
                        ))}
                      </div>

                      {order.mpesa_code && (
                        <p className="text-sm mb-3 p-2 bg-gray-100 rounded">
                          M-Pesa Code: <strong>{order.mpesa_code}</strong>
                        </p>
                      )}

                      <div className="flex items-center justify-between pt-3 border-t">
                        <p className="font-display font-bold">KES {order.total_amount.toLocaleString()}</p>
                        <div className="flex gap-2">
                          <Button
                            data-testid={`reject-order-${order.order_id}`}
                            variant="outline"
                            size="sm"
                            onClick={() => rejectOrder(order.order_id)}
                            className="border-2 border-red-500 text-red-500 hover:bg-red-50"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                          <Button
                            data-testid={`fulfill-order-${order.order_id}`}
                            size="sm"
                            onClick={() => fulfillOrder(order.order_id)}
                            className="bg-hh-green text-black border-2 border-black hover:bg-green-600"
                          >
                            <Check className="w-4 h-4 mr-1" />
                            Fulfill
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* STOCK TAB */}
            <TabsContent value="stock" className="space-y-4">
              <h2 className="font-display text-xl uppercase">Stock Management</h2>
              
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {products.map((product) => (
                  <div
                    key={product.product_id}
                    data-testid={`stock-card-${product.product_id}`}
                    className={`p-4 border-2 border-black rounded-lg shadow-brutal-sm bg-white ${!product.active ? 'opacity-50' : ''}`}
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div className="flex items-center gap-2">
                        <div 
                          className="w-6 h-6 rounded-full border-2 border-black"
                          style={{ backgroundColor: product.color }}
                        />
                        <p className="font-display text-sm uppercase">{product.name.replace('Happy Hour Jaba - ', '')}</p>
                      </div>
                      {!product.active && <Badge variant="destructive">Inactive</Badge>}
                    </div>

                    <div className="flex items-center justify-between mb-3">
                      <div>
                        <p className="text-xs text-gray-500">Current Stock</p>
                        <p className={`font-display text-2xl font-bold ${product.stock < 10 ? 'text-red-500' : ''}`}>
                          {product.stock}
                        </p>
                      </div>
                      <p className="font-display">KES {product.price}</p>
                    </div>

                    {editingStock === product.product_id ? (
                      <div className="space-y-2">
                        <div>
                          <Label className="text-xs">Quantity to Add</Label>
                          <Input
                            type="number"
                            value={newStockValue}
                            onChange={(e) => setNewStockValue(parseInt(e.target.value) || 0)}
                            className="border-2 border-black"
                            placeholder="Quantity to add"
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Manufacturing Date *</Label>
                          <Input
                            type="date"
                            value={manufacturingDate}
                            onChange={(e) => setManufacturingDate(e.target.value)}
                            className="border-2 border-black"
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Batch ID *</Label>
                          <Input
                            value={batchId}
                            onChange={(e) => setBatchId(e.target.value)}
                            className="border-2 border-black"
                            placeholder="e.g., BATCH-2026-001"
                          />
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" onClick={() => {
                            setEditingStock(null);
                            setNewStockValue(0);
                            setManufacturingDate('');
                            setBatchId('');
                          }} variant="outline" className="flex-1">
                            Cancel
                          </Button>
                          <Button size="sm" onClick={updateStock} className="flex-1 bg-hh-green text-black">
                            <Plus className="w-3 h-3 mr-1" />
                            Add Stock
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {product.last_batch_id && (
                          <p className="text-xs text-gray-500">
                            Last: {product.last_batch_id} ({product.last_manufacturing_date})
                          </p>
                        )}
                        <div className="flex gap-2">
                          <Button
                            data-testid={`edit-stock-${product.product_id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setEditingStock(product.product_id);
                              setNewStockValue(0);
                            }}
                            className="flex-1 border-2 border-black"
                          >
                            <Plus className="w-3 h-3 mr-1" />
                            Add Stock
                          </Button>
                          <Button
                            data-testid={`delete-product-${product.product_id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => deleteProduct(product.product_id)}
                            className="border-2 border-red-500 text-red-500"
                          >
                            <X className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </TabsContent>

            {/* RECONCILIATION TAB */}
            <TabsContent value="reconciliation" className="space-y-4">
              <h2 className="font-display text-xl uppercase">Credit Reconciliation</h2>
              
              {reconciliation.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
                  <Check className="w-12 h-12 mx-auto text-hh-green mb-3" />
                  <p className="text-gray-500">All balances cleared</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {reconciliation.map((item) => (
                    <div
                      key={item.user.user_id}
                      data-testid={`reconcile-user-${item.user.user_id}`}
                      className="p-4 border-2 border-black rounded-lg shadow-brutal-sm bg-white"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="font-display font-bold">{item.user.name}</p>
                          <p className="text-sm text-gray-600">{item.user.email}</p>
                          <p className="text-sm text-gray-600">{item.user.phone}</p>
                        </div>
                        <div className="text-right">
                          <p className="text-xs text-gray-500">Outstanding</p>
                          <p className="font-display text-xl font-bold text-red-500">
                            KES {item.outstanding_balance.toLocaleString()}
                          </p>
                        </div>
                      </div>

                      <details className="mt-3">
                        <summary className="cursor-pointer text-sm text-gray-600 hover:text-black">
                          View {item.orders.length} orders
                        </summary>
                        <div className="mt-2 space-y-2 text-sm">
                          {item.orders.slice(0, 5).map((order) => (
                            <div key={order.order_id} className="flex justify-between p-2 bg-gray-50 rounded">
                              <span>{order.order_id}</span>
                              <span>KES {order.total_amount.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* DEFAULTERS TAB */}
            <TabsContent value="defaulters" className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h2 className="font-display text-xl uppercase">Monthly Defaulters</h2>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      data-testid="defaulters-search"
                      placeholder="Search by name..."
                      value={defaultersSearch}
                      onChange={(e) => {
                        setDefaultersSearch(e.target.value);
                        fetchDefaulters(e.target.value);
                      }}
                      className="pl-10 border-2 border-black w-48"
                    />
                  </div>
                </div>
              </div>
              
              {defaulters.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
                  <Check className="w-12 h-12 mx-auto text-hh-green mb-3" />
                  <p className="text-gray-500">No defaulters this month</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {defaulters.map((item) => (
                    <div
                      key={item.user.user_id}
                      data-testid={`defaulter-${item.user.user_id}`}
                      className="p-4 border-2 border-red-500 rounded-lg shadow-brutal-sm bg-red-50"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="font-display font-bold">{item.user.name}</p>
                          <p className="text-sm text-gray-600">{item.user.email}</p>
                          <p className="text-sm text-gray-600">{item.user.phone}</p>
                        </div>
                        <AlertTriangle className="w-6 h-6 text-red-500" />
                      </div>

                      <div className="p-3 bg-white rounded-lg border-2 border-black text-center">
                        <p className="text-xs text-gray-500">Outstanding Balance</p>
                        <p className="font-display text-2xl font-bold text-red-600">
                          KES {item.total_due.toLocaleString()}
                        </p>
                      </div>
                      
                      <details className="mt-3">
                        <summary className="cursor-pointer text-sm text-gray-600 hover:text-black">
                          View {item.orders?.length || 0} orders
                        </summary>
                        <div className="mt-2 space-y-2 text-sm">
                          {item.orders?.slice(0, 5).map((order) => (
                            <div key={order.order_id} className="flex justify-between p-2 bg-white rounded border">
                              <span>{order.order_id}</span>
                              <span>KES {order.total_amount?.toLocaleString()}</span>
                            </div>
                          ))}
                        </div>
                      </details>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* CREDIT PURCHASE INVOICES TAB */}
            <TabsContent value="credit-invoices" className="space-y-4">
              <CreditInvoiceModule users={users} onRefresh={loadAllData} />
            </TabsContent>

            {/* MANUAL INVOICES TAB */}
            <TabsContent value="invoices" className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl uppercase">Manual Invoices</h2>
                <Button
                  data-testid="create-invoice-btn"
                  onClick={() => setShowInvoiceDialog(true)}
                  className="bg-hh-green text-black border-2 border-black shadow-brutal-sm"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Create Invoice
                </Button>
              </div>

              {manualInvoices.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
                  <FileText className="w-12 h-12 mx-auto text-gray-400 mb-3" />
                  <p className="text-gray-500">No manual invoices</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {manualInvoices.map((invoice) => (
                    <div
                      key={invoice.invoice_id}
                      data-testid={`invoice-${invoice.invoice_id}`}
                      className="p-4 border-2 border-black rounded-lg shadow-brutal-sm bg-white"
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="font-display font-bold">{invoice.invoice_id}</p>
                          <p className="text-sm text-gray-600">
                            {invoice.customer_name || users.find(u => u.user_id === invoice.user_id)?.name || 'Unknown'}
                          </p>
                          <p className="text-xs text-gray-500">
                            {format(new Date(invoice.created_at), 'MMM dd, yyyy')}
                          </p>
                        </div>
                        <Badge className={
                          invoice.status === 'verified' ? 'bg-hh-green text-black' :
                          invoice.status === 'rejected' ? 'bg-red-500' : 'bg-yellow-400 text-black'
                        }>
                          {invoice.status}
                        </Badge>
                      </div>

                      <p className="text-sm mb-2">{invoice.description}</p>
                      <div className="flex items-center justify-between">
                        <p className="font-display font-bold">KES {invoice.amount.toLocaleString()}</p>
                        
                        {invoice.status === 'pending' && (
                          <div className="flex gap-2">
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => rejectInvoice(invoice.invoice_id)}
                              className="border-2 border-red-500 text-red-500"
                            >
                              <X className="w-4 h-4" />
                            </Button>
                            <Button
                              size="sm"
                              onClick={() => verifyInvoice(invoice.invoice_id)}
                              className="bg-hh-green text-black border-2 border-black"
                            >
                              <Check className="w-4 h-4" />
                            </Button>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* FEEDBACK TAB */}
            <TabsContent value="feedback" className="space-y-4">
              <h2 className="font-display text-xl uppercase">Customer Feedback</h2>
              
              {feedback.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
                  <MessageSquare className="w-12 h-12 mx-auto text-gray-400 mb-3" />
                  <p className="text-gray-500">No feedback yet</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {feedback.map((fb) => (
                    <div
                      key={fb.feedback_id}
                      data-testid={`feedback-${fb.feedback_id}`}
                      className={`p-4 border-2 border-black rounded-lg shadow-brutal-sm ${fb.status === 'new' ? 'bg-purple-50' : 'bg-white'}`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-display font-bold">{fb.user_name}</p>
                          <p className="text-sm text-gray-600">{fb.user_email}</p>
                        </div>
                        {fb.status === 'new' && (
                          <Badge className="bg-purple-500 text-white">NEW</Badge>
                        )}
                      </div>
                      <p className="text-xs text-gray-500 mb-2">{fb.subject}</p>
                      <p className="text-sm bg-gray-100 p-3 rounded-lg">{fb.message}</p>
                      <p className="text-xs text-gray-400 mt-2">
                        {format(new Date(fb.created_at), 'MMM dd, yyyy • HH:mm')}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </main>

      {/* Create Invoice Dialog */}
      <Dialog open={showInvoiceDialog} onOpenChange={setShowInvoiceDialog}>
        <DialogContent className="max-w-md border-2 border-black shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Create Manual Invoice</DialogTitle>
            <DialogDescription>Create an invoice for cash transactions</DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <div>
              <Label className="font-display uppercase text-sm">Customer</Label>
              <Select 
                value={invoiceForm.user_id} 
                onValueChange={(v) => setInvoiceForm(prev => ({ ...prev, user_id: v }))}
              >
                <SelectTrigger className="border-2 border-black">
                  <SelectValue placeholder="Select user (optional)" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">Manual Entry</SelectItem>
                  {users.map(u => (
                    <SelectItem key={u.user_id} value={u.user_id}>{u.name}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {invoiceForm.user_id === 'none' && (
              <div>
                <Label className="font-display uppercase text-sm">Customer Name</Label>
                <Input
                  value={invoiceForm.customer_name}
                  onChange={(e) => setInvoiceForm(prev => ({ ...prev, customer_name: e.target.value }))}
                  className="border-2 border-black"
                  placeholder="Enter customer name"
                />
              </div>
            )}

            <div>
              <Label className="font-display uppercase text-sm">Amount (KES)</Label>
              <Input
                type="number"
                value={invoiceForm.amount}
                onChange={(e) => setInvoiceForm(prev => ({ ...prev, amount: e.target.value }))}
                className="border-2 border-black"
                placeholder="500"
              />
            </div>

            <div>
              <Label className="font-display uppercase text-sm">Description</Label>
              <Textarea
                value={invoiceForm.description}
                onChange={(e) => setInvoiceForm(prev => ({ ...prev, description: e.target.value }))}
                className="border-2 border-black"
                placeholder="e.g., Cash payment for 2 bottles"
              />
            </div>

            <div>
              <Label className="font-display uppercase text-sm">Payment Method</Label>
              <Select 
                value={invoiceForm.payment_method} 
                onValueChange={(v) => setInvoiceForm(prev => ({ ...prev, payment_method: v }))}
              >
                <SelectTrigger className="border-2 border-black">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="credit">Credit</SelectItem>
                  <SelectItem value="mpesa">M-Pesa</SelectItem>
                </SelectContent>
              </Select>
            </div>

            {invoiceForm.payment_method === 'mpesa' && (
              <div>
                <Label className="font-display uppercase text-sm">M-Pesa Code</Label>
                <Input
                  value={invoiceForm.mpesa_code}
                  onChange={(e) => setInvoiceForm(prev => ({ ...prev, mpesa_code: e.target.value.toUpperCase() }))}
                  className="border-2 border-black uppercase"
                  placeholder="ABC123XYZ"
                />
              </div>
            )}

            <Button
              data-testid="submit-invoice-btn"
              onClick={createManualInvoice}
              className="w-full h-12 bg-hh-green text-black border-2 border-black shadow-brutal"
            >
              Create Invoice
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Cancel Order Dialog */}
      <Dialog open={showCancelDialog} onOpenChange={setShowCancelDialog}>
        <DialogContent className="max-w-md border-2 border-black shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Cancel Order</DialogTitle>
            <DialogDescription>Provide a reason for cancellation (required)</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              data-testid="cancel-reason-input"
              placeholder="Enter cancellation reason (minimum 5 characters)..."
              value={cancelReason}
              onChange={(e) => setCancelReason(e.target.value)}
              className="border-2 border-black min-h-[100px]"
            />
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => {
                  setShowCancelDialog(false);
                  setCancellingOrder(null);
                  setCancelReason('');
                }}
                className="flex-1 border-2 border-black"
              >
                Back
              </Button>
              <Button
                data-testid="confirm-cancel-btn"
                onClick={cancelOrder}
                className="flex-1 bg-red-500 text-white border-2 border-black"
              >
                Cancel Order
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Push Offer Dialog */}
      <Dialog open={showOfferDialog} onOpenChange={setShowOfferDialog}>
        <DialogContent className="max-w-md border-2 border-black shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Push Offer</DialogTitle>
            <DialogDescription>Send promotional notification to all customers</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="font-display uppercase text-sm">Offer Title</Label>
              <Input
                data-testid="offer-title-input"
                placeholder="e.g., Buy 1 Get 1 Free!"
                value={offerTitle}
                onChange={(e) => setOfferTitle(e.target.value)}
                className="border-2 border-black"
              />
            </div>
            <div>
              <Label className="font-display uppercase text-sm">Offer Message</Label>
              <Textarea
                data-testid="offer-message-input"
                placeholder="Describe the offer details..."
                value={offerMessage}
                onChange={(e) => setOfferMessage(e.target.value)}
                className="border-2 border-black min-h-[100px]"
              />
            </div>
            <Button
              data-testid="send-offer-btn"
              onClick={sendPushOffer}
              className="w-full h-12 bg-purple-600 text-white border-2 border-black shadow-brutal"
            >
              <Gift className="w-4 h-4 mr-2" />
              Send to All Customers
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Auto Generate Invoice Dialog */}
      <Dialog open={showAutoInvoiceDialog} onOpenChange={setShowAutoInvoiceDialog}>
        <DialogContent className="max-w-md border-2 border-black shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Auto Generate Invoice</DialogTitle>
            <DialogDescription>Create invoice from customer's credit purchase history</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="font-display uppercase text-sm">Customer</Label>
              <Select value={autoInvoiceUserId} onValueChange={setAutoInvoiceUserId}>
                <SelectTrigger className="border-2 border-black">
                  <SelectValue placeholder="Select customer" />
                </SelectTrigger>
                <SelectContent>
                  {users.map(u => (
                    <SelectItem key={u.user_id} value={u.user_id}>
                      {u.name} ({u.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="font-display uppercase text-sm">Start Date</Label>
                <Input
                  type="date"
                  value={autoInvoiceStartDate}
                  onChange={(e) => setAutoInvoiceStartDate(e.target.value)}
                  className="border-2 border-black"
                />
              </div>
              <div>
                <Label className="font-display uppercase text-sm">End Date</Label>
                <Input
                  type="date"
                  value={autoInvoiceEndDate}
                  onChange={(e) => setAutoInvoiceEndDate(e.target.value)}
                  className="border-2 border-black"
                />
              </div>
            </div>
            <Button
              data-testid="generate-auto-invoice-btn"
              onClick={autoGenerateInvoice}
              className="w-full h-12 bg-hh-green text-black border-2 border-black shadow-brutal"
            >
              <Calendar className="w-4 h-4 mr-2" />
              Generate Invoice
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
