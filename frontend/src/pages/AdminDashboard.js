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
  Search, Gift, MessageSquare, Share2, Calendar, Bell, Trash2, ChevronDown, ChevronUp, Send, Shield, Wrench, UserCog
} from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';
import CreditInvoiceModule from '../components/CreditInvoiceModule';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;
const MONTHLY_CREDIT_LIMIT = 30000;

const AdminDashboard = () => {
  const navigate = useNavigate();
  const { user, isAdmin, isSuperAdmin, checkAuth } = useAuth();
  const [activeTab, setActiveTab] = useState('pending');
  
  // Role Switcher State (Super Admin only)
  const [activeRole, setActiveRole] = useState(user?.role || 'admin');
  const [showRoleSwitcher, setShowRoleSwitcher] = useState(false);
  
  // Pending Orders State
  const [pendingOrders, setPendingOrders] = useState([]);
  const [pendingFilter, setPendingFilter] = useState('all');
  const [showCancelDialog, setShowCancelDialog] = useState(false);
  const [cancellingOrder, setCancellingOrder] = useState(null);
  const [cancelReason, setCancelReason] = useState('');
  
  // Stock State
  const [products, setProducts] = useState([]);
  const [stockEntries, setStockEntries] = useState([]);
  const [stockLedgerProductFilter, setStockLedgerProductFilter] = useState('all');
  const [stockLedgerBatchFilter, setStockLedgerBatchFilter] = useState('');
  const [stockLedgerFromDate, setStockLedgerFromDate] = useState('');
  const [stockLedgerToDate, setStockLedgerToDate] = useState('');
  const [stockLedgerRowLimit, setStockLedgerRowLimit] = useState('100');
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

  // Payment Verification State
  const [pendingPayments, setPendingPayments] = useState([]);
  const [verifyRejectReason, setVerifyRejectReason] = useState('');
  const [verifyingPayment, setVerifyingPayment] = useState(null);
  const [showRejectDialog, setShowRejectDialog] = useState(false);
  
  // Transaction Match State
  const [showMatchDialog, setShowMatchDialog] = useState(false);
  const [matchingPop, setMatchingPop] = useState(null);
  const [adminTxCode, setAdminTxCode] = useState('');
  const [adminAmount, setAdminAmount] = useState('');
  
  // Force Approve State
  const [showForceApproveDialog, setShowForceApproveDialog] = useState(false);
  const [forceApprovePop, setForceApprovePop] = useState(null);
  const [forceApproveReason, setForceApproveReason] = useState('');
  
  // Dispute Chat State
  const [disputes, setDisputes] = useState([]);
  const [selectedDispute, setSelectedDispute] = useState(null);
  const [disputeMessages, setDisputeMessages] = useState([]);
  const [newDisputeMsg, setNewDisputeMsg] = useState('');
  const [showDisputeChat, setShowDisputeChat] = useState(false);
  
  // Starting Credit Import State
  const [showBacklogDialog, setShowBacklogDialog] = useState(false);
  const [backlogUserId, setBacklogUserId] = useState('');
  const [backlogAmount, setBacklogAmount] = useState('');
  const [backlogDescription, setBacklogDescription] = useState('');
  
  // Share Reconciliation Report State
  const [showShareReportDialog, setShowShareReportDialog] = useState(false);
  const [reportUserId, setReportUserId] = useState('');
  const [reportStartDate, setReportStartDate] = useState('');
  const [reportEndDate, setReportEndDate] = useState('');
  const [reportPreview, setReportPreview] = useState(null);
  
  // User to delete
  const [userToDelete, setUserToDelete] = useState(null);
  const [showDeleteUserDialog, setShowDeleteUserDialog] = useState(false);
  
  // Admin notification state
  const [adminNotifications, setAdminNotifications] = useState([]);
  const [unreadNotifCount, setUnreadNotifCount] = useState(0);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);
  const [lastNotifCheck, setLastNotifCheck] = useState(null);
  
  // Expanded reconciliation rows
  const [expandedUsers, setExpandedUsers] = useState({});
  
  const [users, setUsers] = useState([]);
  const [approvedDomains, setApprovedDomains] = useState([]);
  const [newApprovedDomain, setNewApprovedDomain] = useState('');
  const [updatingUserRoleId, setUpdatingUserRoleId] = useState(null);
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

  // Poll for admin notifications every 15 seconds
  useEffect(() => {
    fetchAdminNotifications();
    const interval = setInterval(() => {
      fetchAdminNotifications();
    }, 15000);
    return () => clearInterval(interval);
  }, []);

  const fetchAdminNotifications = async () => {
    try {
      const response = await axios.get(`${API}/notifications`, { withCredentials: true });
      const notifs = response.data;
      setAdminNotifications(notifs);
      
      const unread = notifs.filter(n => !n.read).length;
      
      // Show toast for new order notifications
      if (lastNotifCheck !== null && unread > unreadNotifCount) {
        const newNotifs = notifs.filter(n => !n.read && n.notification_type === 'order');
        if (newNotifs.length > 0) {
          const latest = newNotifs[0];
          toast.info(latest.message, { 
            description: latest.title,
            duration: 5000 
          });
        }
      }
      
      setUnreadNotifCount(unread);
      setLastNotifCheck(Date.now());
    } catch (error) {
      // Silently fail for notification polling
    }
  };

  const markNotificationRead = async (notificationId) => {
    try {
      await axios.put(`${API}/notifications/${notificationId}/read`, {}, { withCredentials: true });
      fetchAdminNotifications();
    } catch (error) {
      // Silently fail
    }
  };

  const markAllNotificationsRead = async () => {
    try {
      const unreadNotifs = adminNotifications.filter(n => !n.read);
      await Promise.all(unreadNotifs.map(n => 
        axios.put(`${API}/notifications/${n.notification_id}/read`, {}, { withCredentials: true })
      ));
      fetchAdminNotifications();
      toast.success('All notifications marked as read');
    } catch (error) {
      toast.error('Failed to mark notifications as read');
    }
  };

  const toggleExpandUser = (userId) => {
    setExpandedUsers(prev => ({ ...prev, [userId]: !prev[userId] }));
  };

  const loadAllData = async () => {
    setLoading(true);
    try {
      const requests = [
        fetchPendingOrders(),
        fetchProducts(),
        fetchStockEntries(),
        fetchReconciliation(),
        fetchDefaulters(),
        fetchPendingPayments(),
        fetchDisputes(),
        fetchUsers(),
        fetchFeedback()
      ];
      if (isSuperAdmin) {
        requests.push(fetchApprovedDomains());
      }
      await Promise.all(requests);
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

  const fetchStockEntries = async () => {
    try {
      const response = await axios.get(`${API}/admin/stock-entries?limit=500`, { withCredentials: true });
      setStockEntries(response.data || []);
    } catch (error) {
      console.error('Failed to fetch stock entries');
    }
  };

  const getFilteredStockLedgerEntries = () => {
    const fromDate = stockLedgerFromDate ? new Date(`${stockLedgerFromDate}T00:00:00`) : null;
    const toDate = stockLedgerToDate ? new Date(`${stockLedgerToDate}T23:59:59`) : null;
    const batchQuery = stockLedgerBatchFilter.trim().toLowerCase();

    return stockEntries.filter((entry) => {
      if (stockLedgerProductFilter !== 'all' && String(entry.product_id) !== stockLedgerProductFilter) {
        return false;
      }

      if (batchQuery) {
        const batchValue = (entry.batch_id || '').toLowerCase();
        const productValue = (entry.product_name || '').toLowerCase();
        if (!batchValue.includes(batchQuery) && !productValue.includes(batchQuery)) {
          return false;
        }
      }

      if (fromDate || toDate) {
        const entryDate = entry.created_at ? new Date(entry.created_at) : null;
        if (!entryDate || Number.isNaN(entryDate.getTime())) {
          return false;
        }
        if (fromDate && entryDate < fromDate) {
          return false;
        }
        if (toDate && entryDate > toDate) {
          return false;
        }
      }

      return true;
    });
  };

  const exportStockLedgerCsv = () => {
    const filteredEntries = getFilteredStockLedgerEntries();
    if (filteredEntries.length === 0) {
      toast.error('No stock ledger rows to export');
      return;
    }

    const rows = [
      ['Entry ID', 'Product', 'Product ID', 'Quantity Added', 'Batch ID', 'Manufacturing Date', 'Created At'],
      ...filteredEntries.map((entry) => [
        entry.entry_id,
        entry.product_name || '',
        entry.product_id,
        entry.quantity_added,
        entry.batch_id || '',
        entry.manufacturing_date || '',
        entry.created_at || ''
      ])
    ];

    const escapeCell = (value) => `"${String(value ?? '').replace(/"/g, '""')}"`;
    const csvContent = rows.map((row) => row.map(escapeCell).join(',')).join('\n');

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    const stamp = format(new Date(), 'yyyyMMdd-HHmmss');
    link.href = url;
    link.download = `stock-ledger-${stamp}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
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

  const fetchPendingPayments = async () => {
    try {
      const response = await axios.get(`${API}/admin/payments/pending`, { withCredentials: true });
      setPendingPayments(response.data);
    } catch (error) {
      console.error('Failed to fetch pending payments');
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

  const fetchApprovedDomains = async () => {
    try {
      const response = await axios.get(`${API}/admin/domains`, { withCredentials: true });
      setApprovedDomains(response.data);
    } catch (error) {
      console.error('Failed to fetch approved domains');
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
      fetchStockEntries();
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

  // Fetch Reconciliation Report Preview
  const fetchReportPreview = async (userId, startDate, endDate) => {
    try {
      const params = new URLSearchParams();
      if (startDate) params.append('start_date', startDate);
      if (endDate) params.append('end_date', endDate);
      const response = await axios.get(`${API}/admin/users/${userId}/reconciliation-report?${params.toString()}`, { withCredentials: true });
      setReportPreview(response.data);
    } catch (error) {
      toast.error('Failed to fetch report');
    }
  };

  // Share Reconciliation Report
  const shareReconciliationReport = async () => {
    if (!reportUserId) {
      toast.error('Please select a user');
      return;
    }
    try {
      await axios.post(`${API}/admin/users/${reportUserId}/send-reconciliation`, {
        start_date: reportStartDate,
        end_date: reportEndDate
      }, { withCredentials: true });
      toast.success('Reconciliation report sent to user');
      setShowShareReportDialog(false);
      setReportUserId('');
      setReportStartDate('');
      setReportEndDate('');
      setReportPreview(null);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send report');
    }
  };

  // Delete User
  const deleteUser = async (userId) => {
    try {
      await axios.delete(`${API}/admin/users/${userId}`, { withCredentials: true });
      toast.success('User deleted successfully');
      setUserToDelete(null);
      fetchUsers();
      fetchReconciliation();
      fetchDefaulters();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to delete user');
    }
  };

  const addApprovedDomain = async () => {
    if (!newApprovedDomain.trim()) {
      toast.error('Enter a domain name');
      return;
    }

    try {
      const normalizedDomain = newApprovedDomain.trim().replace(/^@/, '');
      await axios.post(`${API}/admin/domains`, { domain: normalizedDomain }, { withCredentials: true });
      toast.success(`Domain ${normalizedDomain} saved`);
      setNewApprovedDomain('');
      fetchApprovedDomains();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save domain');
    }
  };

  const disableApprovedDomain = async (domain) => {
    try {
      await axios.delete(`${API}/admin/domains/${encodeURIComponent(domain)}`, { withCredentials: true });
      toast.success(`Domain ${domain} disabled`);
      fetchApprovedDomains();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to disable domain');
    }
  };

  const updateUserRoleAssignment = async (userId, role) => {
    try {
      setUpdatingUserRoleId(userId);
      const response = await axios.put(
        `${API}/admin/users/${userId}/role`,
        { role },
        { withCredentials: true }
      );
      toast.success(`${response.data.name || response.data.email} is now ${role.replace('_', ' ')}`);
      await fetchUsers();
      if (checkAuth) {
        await checkAuth();
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update role');
    } finally {
      setUpdatingUserRoleId(null);
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
  // Payment Verification Actions
  const matchTransaction = async () => {
    if (!matchingPop || !adminTxCode || !adminAmount) {
      toast.error('Please enter both transaction code and amount');
      return;
    }
    try {
      const response = await axios.post(`${API}/admin/payments/${matchingPop.pop_id}/match`, {
        admin_transaction_code: adminTxCode.toUpperCase(),
        admin_amount: parseFloat(adminAmount)
      }, { withCredentials: true });
      
      if (response.data.status === 'approved') {
        toast.success('Transaction matched and approved!');
      } else {
        toast.error(`Verification failed: ${response.data.message}`);
      }
      setShowMatchDialog(false);
      setMatchingPop(null);
      setAdminTxCode('');
      setAdminAmount('');
      fetchPendingPayments();
      fetchDisputes();
      fetchReconciliation();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Match failed');
    }
  };

  const forceApprovePayment = async () => {
    if (!forceApprovePop || !forceApproveReason || forceApproveReason.trim().length < 5) {
      toast.error('Please provide a detailed reason (min 5 chars)');
      return;
    }
    try {
      await axios.post(`${API}/admin/payments/${forceApprovePop.pop_id}/force-approve`, {
        reason: forceApproveReason
      }, { withCredentials: true });
      toast.success('Payment force-approved');
      setShowForceApproveDialog(false);
      setForceApprovePop(null);
      setForceApproveReason('');
      fetchPendingPayments();
      fetchDisputes();
      fetchReconciliation();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Force approve failed');
    }
  };

  const rejectPayment = async () => {
    if (!verifyingPayment || !verifyRejectReason) {
      toast.error('Please provide a rejection reason');
      return;
    }
    try {
      await axios.post(`${API}/admin/payments/${verifyingPayment}/reject`, {
        status: 'rejected',
        reason: verifyRejectReason
      }, { withCredentials: true });
      toast.success('Payment rejected');
      setShowRejectDialog(false);
      setVerifyingPayment(null);
      setVerifyRejectReason('');
      fetchPendingPayments();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject payment');
    }
  };

  // Dispute Chat Functions
  const fetchDisputes = async () => {
    try {
      const response = await axios.get(`${API}/admin/disputes`, { withCredentials: true });
      setDisputes(response.data);
    } catch (error) {
      console.error('Failed to fetch disputes');
    }
  };

  const openDisputeChat = async (dispute) => {
    setSelectedDispute(dispute);
    setShowDisputeChat(true);
    try {
      const response = await axios.get(`${API}/disputes/${dispute.pop_id}/messages`, { withCredentials: true });
      setDisputeMessages(response.data.messages || []);
    } catch (error) {
      toast.error('Failed to load messages');
    }
  };

  const sendAdminReply = async () => {
    if (!newDisputeMsg.trim() || !selectedDispute) return;
    try {
      await axios.post(`${API}/disputes/message`, {
        pop_id: selectedDispute.pop_id,
        message: newDisputeMsg
      }, { withCredentials: true });
      setNewDisputeMsg('');
      // Reload messages
      const response = await axios.get(`${API}/disputes/${selectedDispute.pop_id}/messages`, { withCredentials: true });
      setDisputeMessages(response.data.messages || []);
      fetchDisputes();
    } catch (error) {
      toast.error('Failed to send message');
    }
  };

  const submitBacklogCredit = async () => {
    if (!backlogUserId || !backlogAmount || !backlogDescription) {
      toast.error('Please fill all fields');
      return;
    }
    try {
      await axios.post(`${API}/admin/starting-credit`, {
        user_id: backlogUserId,
        amount: parseFloat(backlogAmount),
        description: backlogDescription
      }, { withCredentials: true });
      toast.success('Starting credit imported');
      setShowBacklogDialog(false);
      setBacklogUserId('');
      setBacklogAmount('');
      setBacklogDescription('');
      fetchReconciliation();
      fetchDefaulters();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import starting credit');
    }
  };

  const sendDefaulterWarning = async (userId, template) => {
    try {
      const response = await axios.post(`${API}/admin/defaulter-warning/${userId}?template=${template}`, {}, { withCredentials: true });
      toast.success(response.data.message);
      // Open WhatsApp if link available
      if (response.data.whatsapp_link) {
        window.open(response.data.whatsapp_link, '_blank');
      }
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to send warning');
    }
  };

  // Role Switcher Functions (Super Admin only)
  const switchRole = async (targetRole) => {
    try {
      await axios.post(`${API}/admin/switch-role?target_role=${targetRole}`, {}, { withCredentials: true });
      setActiveRole(targetRole);
      setShowRoleSwitcher(false);
      
      if (targetRole === 'user') {
        toast.info('Switched to User view — redirecting to customer dashboard');
        navigate('/dashboard');
        return;
      }
      toast.success(`Switched to ${targetRole === 'super_admin' ? 'Super Admin' : 'Admin'} view`);
      if (checkAuth) checkAuth();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to switch role');
    }
  };

  const resetAllTestData = async () => {
    if (!window.confirm('This will DELETE all orders, invoices, payments, disputes, and notifications. Are you sure?')) return;
    try {
      const response = await axios.post(`${API}/admin/maintenance/reset-test-data`, {}, { withCredentials: true });
      toast.success(`Test data cleared: ${response.data.deleted.orders} orders, ${response.data.deleted.invoices} invoices, ${response.data.deleted.payments} payments`);
      loadAllData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset data');
    }
  };

  const resetDailyCounters = async () => {
    if (!window.confirm("Reset today's order counters? This removes today's orders.")) return;
    try {
      const response = await axios.post(`${API}/admin/maintenance/reset-counters`, {}, { withCredentials: true });
      toast.success(response.data.message);
      fetchPendingOrders();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reset counters');
    }
  };

  useEffect(() => {
    if (activeTab === 'pending') fetchPendingOrders();
  }, [pendingFilter]);

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col" onClick={() => showNotifDropdown && setShowNotifDropdown(false)}>
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
                {isSuperAdmin ? 'Super Admin' : 'Admin'} Dashboard
              </h1>
              <p className="text-xs text-gray-400">Happy Hour Jaba, Nairobi</p>
            </div>
          </div>
          <div className="flex gap-2 items-center">
            {/* Role Switcher (Super Admin only) */}
            {isSuperAdmin && (
              <div className="relative" onClick={(e) => e.stopPropagation()}>
                <Button
                  data-testid="role-switcher-btn"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowRoleSwitcher(!showRoleSwitcher)}
                  className="text-white hover:bg-gray-800 gap-1"
                >
                  <UserCog className="w-4 h-4" />
                  <span className="text-xs hidden sm:inline">
                    {activeRole === 'super_admin' ? 'SA' : activeRole === 'admin' ? 'Admin' : 'User'}
                  </span>
                </Button>
                {showRoleSwitcher && (
                  <div className="absolute right-0 top-full mt-2 w-48 bg-white border-2 border-black rounded-lg shadow-brutal-lg z-50">
                    <div className="p-2 border-b-2 border-black bg-gray-50">
                      <p className="font-display text-xs uppercase font-bold text-black">Switch Role</p>
                    </div>
                    {['super_admin', 'admin', 'user'].map((r) => (
                      <button
                        key={r}
                        data-testid={`switch-to-${r}`}
                        onClick={() => switchRole(r)}
                        className={`w-full p-3 text-left text-sm hover:bg-gray-50 flex items-center gap-2 ${
                          activeRole === r ? 'bg-hh-green/20 font-bold' : ''
                        } text-black`}
                      >
                        <div className={`w-2 h-2 rounded-full ${
                          r === 'super_admin' ? 'bg-purple-500' : r === 'admin' ? 'bg-hh-green' : 'bg-blue-500'
                        }`} />
                        {r === 'super_admin' ? 'Super Admin' : r === 'admin' ? 'Admin' : 'User'}
                        {activeRole === r && <Check className="w-3 h-3 ml-auto text-black" />}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            {/* Notification Bell */}
            <div className="relative">
              <Button
                data-testid="admin-notifications-bell"
                variant="ghost"
                size="sm"
                onClick={(e) => { e.stopPropagation(); setShowNotifDropdown(!showNotifDropdown); }}
                className="text-white hover:bg-gray-800 relative"
                title="Notifications"
              >
                <Bell className="w-4 h-4" />
                {unreadNotifCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-red-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center font-bold">
                    {unreadNotifCount > 9 ? '9+' : unreadNotifCount}
                  </span>
                )}
              </Button>
              
              {/* Notification Dropdown */}
              {showNotifDropdown && (
                <div className="absolute right-0 top-full mt-2 w-80 bg-white border-2 border-black rounded-lg shadow-brutal-lg z-50 max-h-96 overflow-y-auto">
                  <div className="p-3 border-b-2 border-black bg-gray-50 flex items-center justify-between">
                    <p className="font-display text-sm uppercase font-bold">Notifications</p>
                    {unreadNotifCount > 0 && (
                      <button
                        data-testid="mark-all-read-btn"
                        onClick={markAllNotificationsRead}
                        className="text-xs text-hh-green hover:underline font-medium"
                      >
                        Mark all read
                      </button>
                    )}
                  </div>
                  {adminNotifications.length === 0 ? (
                    <div className="p-4 text-center text-gray-500 text-sm">
                      No notifications
                    </div>
                  ) : (
                    adminNotifications.slice(0, 20).map((notif) => (
                      <div
                        key={notif.notification_id}
                        data-testid={`admin-notif-${notif.notification_id}`}
                        onClick={() => { if (!notif.read) markNotificationRead(notif.notification_id); }}
                        className={`p-3 border-b last:border-b-0 cursor-pointer hover:bg-gray-50 transition-colors ${!notif.read ? 'bg-green-50' : ''}`}
                      >
                        <div className="flex items-start gap-2">
                          {!notif.read && <div className="w-2 h-2 rounded-full bg-hh-green mt-1.5 flex-shrink-0" />}
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-bold truncate">{notif.title}</p>
                            <p className="text-xs text-gray-600 line-clamp-2">{notif.message}</p>
                            <p className="text-xs text-gray-400 mt-1">
                              {notif.created_at ? format(new Date(notif.created_at), 'MMM dd, HH:mm') : ''}
                            </p>
                          </div>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>
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
            <TabsList className="grid w-full grid-cols-4 sm:grid-cols-9 mb-6 border-2 border-black bg-white">
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
                data-testid="tab-payments"
                value="payments" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <CreditCard className="w-4 h-4 mr-1 hidden sm:block" />
                Payments
                {pendingPayments.length > 0 && (
                  <Badge className="ml-1 bg-yellow-500 text-black text-xs">{pendingPayments.length}</Badge>
                )}
              </TabsTrigger>
              <TabsTrigger 
                data-testid="tab-credit-invoices"
                value="credit-invoices" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <Receipt className="w-4 h-4 mr-1 hidden sm:block" />
                Invoices
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
              <TabsTrigger 
                data-testid="tab-messages"
                value="messages" 
                className="font-display uppercase text-xs data-[state=active]:bg-hh-green data-[state=active]:text-black"
              >
                <Mail className="w-4 h-4 mr-1 hidden sm:block" />
                Messages
                {disputes.length > 0 && (
                  <Badge className="ml-1 bg-orange-500 text-white text-xs">{disputes.length}</Badge>
                )}
              </TabsTrigger>
              {isSuperAdmin && (
                <TabsTrigger 
                  data-testid="tab-maintenance"
                  value="maintenance" 
                  className="font-display uppercase text-xs data-[state=active]:bg-purple-500 data-[state=active]:text-white"
                >
                  <Wrench className="w-4 h-4 mr-1 hidden sm:block" />
                  Maint
                </TabsTrigger>
              )}
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
                  <p className="text-gray-500">No recent orders</p>
                </div>
              ) : (
                <div className="grid gap-4 md:grid-cols-2">
                  {pendingOrders.map((order) => (
                    <div
                      key={order.order_id}
                      data-testid={`pending-order-${order.order_id}`}
                      className={`p-4 border-2 rounded-lg shadow-brutal-sm bg-white ${
                        order.status === 'pending' ? 'border-yellow-500' : 'border-black'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-display font-bold">{order.order_id}</p>
                            <Badge className={`text-xs ${
                              order.status === 'pending' ? 'bg-yellow-400 text-black' :
                              order.status === 'fulfilled' ? 'bg-hh-green text-black' :
                              'bg-red-500 text-white'
                            }`}>
                              {order.status}
                            </Badge>
                          </div>
                          <p className="text-sm text-gray-600">{order.user_name}</p>
                          <p className="text-xs text-gray-500">{order.user_phone}</p>
                          {order.created_at && (
                            <p className="text-xs text-gray-400 mt-1">
                              {format(new Date(order.created_at), 'MMM dd, HH:mm')}
                            </p>
                          )}
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
                        {order.status === 'pending' && (
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
                        )}
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
                        {stockEntries.filter((entry) => entry.product_id === product.product_id).length > 0 && (
                          <div className="text-xs text-gray-600 bg-gray-50 border rounded p-2 space-y-1">
                            <p className="font-bold uppercase tracking-wide">Recent Stock Entries</p>
                            {stockEntries
                              .filter((entry) => entry.product_id === product.product_id)
                              .slice(0, 3)
                              .map((entry) => (
                                <div key={entry.entry_id} className="flex justify-between gap-2">
                                  <span>
                                    +{entry.quantity_added} ({entry.batch_id || 'no-batch'})
                                  </span>
                                  <span className="text-gray-500">
                                    {entry.created_at ? format(new Date(entry.created_at), 'MMM dd, HH:mm') : ''}
                                  </span>
                                </div>
                              ))}
                          </div>
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

              <div className="p-4 border-2 border-black rounded-lg shadow-brutal-sm bg-white space-y-4">
                <div className="flex items-center justify-between gap-3 flex-wrap">
                  <h3 className="font-display text-lg uppercase">Stock Ledger</h3>
                  <div className="flex items-center gap-2">
                    <Button
                      size="sm"
                      variant="outline"
                      onClick={fetchStockEntries}
                      className="border-2 border-black"
                    >
                      <RefreshCw className="w-4 h-4 mr-1" />
                      Refresh
                    </Button>
                    <Button
                      size="sm"
                      onClick={exportStockLedgerCsv}
                      className="bg-black text-white hover:bg-gray-800"
                    >
                      Export CSV
                    </Button>
                  </div>
                </div>

                <div className="grid gap-3 md:grid-cols-2 lg:grid-cols-5">
                  <div className="space-y-1">
                    <Label className="text-xs uppercase tracking-wide">Product</Label>
                    <Select value={stockLedgerProductFilter} onValueChange={setStockLedgerProductFilter}>
                      <SelectTrigger className="border-2 border-black">
                        <SelectValue placeholder="All products" />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All products</SelectItem>
                        {products.map((product) => (
                          <SelectItem key={`ledger-product-${product.product_id}`} value={String(product.product_id)}>
                            {product.name.replace('Happy Hour Jaba - ', '')}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs uppercase tracking-wide">Batch/Product Search</Label>
                    <Input
                      value={stockLedgerBatchFilter}
                      onChange={(e) => setStockLedgerBatchFilter(e.target.value)}
                      placeholder="batch id or name"
                      className="border-2 border-black"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs uppercase tracking-wide">From</Label>
                    <Input
                      type="date"
                      value={stockLedgerFromDate}
                      onChange={(e) => setStockLedgerFromDate(e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs uppercase tracking-wide">To</Label>
                    <Input
                      type="date"
                      value={stockLedgerToDate}
                      onChange={(e) => setStockLedgerToDate(e.target.value)}
                      className="border-2 border-black"
                    />
                  </div>

                  <div className="space-y-1">
                    <Label className="text-xs uppercase tracking-wide">Rows</Label>
                    <Select value={stockLedgerRowLimit} onValueChange={setStockLedgerRowLimit}>
                      <SelectTrigger className="border-2 border-black">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="50">50</SelectItem>
                        <SelectItem value="100">100</SelectItem>
                        <SelectItem value="200">200</SelectItem>
                        <SelectItem value="500">500</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>

                {(() => {
                  const filteredEntries = getFilteredStockLedgerEntries();
                  const visibleEntries = filteredEntries.slice(0, parseInt(stockLedgerRowLimit, 10));
                  const totalUnitsAdded = filteredEntries.reduce((sum, entry) => sum + (Number(entry.quantity_added) || 0), 0);
                  const uniqueBatches = new Set(filteredEntries.map((entry) => entry.batch_id).filter(Boolean)).size;

                  return (
                    <>
                      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                        <div className="p-3 border rounded bg-gray-50">
                          <p className="text-xs text-gray-500 uppercase tracking-wide">Filtered Entries</p>
                          <p className="font-display text-xl font-bold">{filteredEntries.length}</p>
                        </div>
                        <div className="p-3 border rounded bg-gray-50">
                          <p className="text-xs text-gray-500 uppercase tracking-wide">Units Added</p>
                          <p className="font-display text-xl font-bold">{totalUnitsAdded}</p>
                        </div>
                        <div className="p-3 border rounded bg-gray-50">
                          <p className="text-xs text-gray-500 uppercase tracking-wide">Unique Batches</p>
                          <p className="font-display text-xl font-bold">{uniqueBatches}</p>
                        </div>
                      </div>

                      {visibleEntries.length === 0 ? (
                        <div className="text-sm text-gray-500 p-4 border border-dashed rounded">
                          No stock ledger rows match current filters.
                        </div>
                      ) : (
                        <div className="overflow-x-auto border-2 border-black rounded-lg">
                          <table className="w-full text-sm">
                            <thead className="bg-black text-hh-green">
                              <tr>
                                <th className="p-2 text-left font-display uppercase text-xs">Timestamp</th>
                                <th className="p-2 text-left font-display uppercase text-xs">Product</th>
                                <th className="p-2 text-left font-display uppercase text-xs">Qty Added</th>
                                <th className="p-2 text-left font-display uppercase text-xs">Batch ID</th>
                                <th className="p-2 text-left font-display uppercase text-xs">MFG Date</th>
                              </tr>
                            </thead>
                            <tbody>
                              {visibleEntries.map((entry) => (
                                <tr key={entry.entry_id} className="border-t bg-white">
                                  <td className="p-2 text-xs">
                                    {entry.created_at ? format(new Date(entry.created_at), 'yyyy-MM-dd HH:mm') : 'N/A'}
                                  </td>
                                  <td className="p-2">
                                    <div className="font-medium">{(entry.product_name || '').replace('Happy Hour Jaba - ', '')}</div>
                                    <div className="text-xs text-gray-500">ID: {entry.product_id}</div>
                                  </td>
                                  <td className="p-2 font-bold text-hh-green">+{entry.quantity_added}</td>
                                  <td className="p-2">{entry.batch_id || 'N/A'}</td>
                                  <td className="p-2">{entry.manufacturing_date || 'N/A'}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      )}
                    </>
                  );
                })()}
              </div>
            </TabsContent>

            {/* RECONCILIATION TAB */}
            <TabsContent value="reconciliation" className="space-y-4">
              <div className="flex items-center justify-between flex-wrap gap-2">
                <h2 className="font-display text-xl uppercase">Credit Reconciliation</h2>
                <div className="flex items-center gap-2">
                  <div className="relative">
                    <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <Input
                      data-testid="reconciliation-search"
                      placeholder="Search by name..."
                      value={reconciliationSearch}
                      onChange={(e) => {
                        setReconciliationSearch(e.target.value);
                        fetchReconciliation(e.target.value);
                      }}
                      className="pl-10 border-2 border-black w-48"
                    />
                  </div>
                </div>
              </div>
              
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

                      {/* Order Summary Stats */}
                      <div className="grid grid-cols-3 gap-2 mb-3 text-center">
                        <div className="p-2 bg-gray-50 rounded border">
                          <p className="text-xs text-gray-500">Orders</p>
                          <p className="font-display font-bold">{item.orders?.length || 0}</p>
                        </div>
                        <div className="p-2 bg-blue-50 rounded border border-blue-200">
                          <p className="text-xs text-gray-500">Pending</p>
                          <p className="font-display font-bold text-blue-600">
                            KES {(item.total_pending || 0).toLocaleString()}
                          </p>
                        </div>
                        <div className="p-2 bg-red-50 rounded border border-red-200">
                          <p className="text-xs text-gray-500">Total Owed</p>
                          <p className="font-display font-bold text-red-600">
                            KES {item.outstanding_balance.toLocaleString()}
                          </p>
                        </div>
                      </div>

                      {/* Expandable Order Breakdown */}
                      <div className="border-t pt-3">
                        <button
                          data-testid={`toggle-orders-${item.user.user_id}`}
                          onClick={() => toggleExpandUser(item.user.user_id)}
                          className="flex items-center gap-2 text-sm text-gray-600 hover:text-black w-full"
                        >
                          {expandedUsers[item.user.user_id] ? (
                            <ChevronUp className="w-4 h-4" />
                          ) : (
                            <ChevronDown className="w-4 h-4" />
                          )}
                          <span className="font-medium">
                            View {item.orders?.length || 0} order details
                          </span>
                        </button>
                        
                        {expandedUsers[item.user.user_id] && item.orders && (
                          <div className="mt-3 border-2 border-gray-200 rounded-lg overflow-hidden">
                            <table className="w-full text-sm">
                              <thead className="bg-black text-hh-green">
                                <tr>
                                  <th className="p-2 text-left font-display uppercase text-xs">Timestamp</th>
                                  <th className="p-2 text-left font-display uppercase text-xs">Flavor</th>
                                  <th className="p-2 text-center font-display uppercase text-xs">Qty</th>
                                  <th className="p-2 text-right font-display uppercase text-xs">Cost</th>
                                  <th className="p-2 text-center font-display uppercase text-xs">Status</th>
                                </tr>
                              </thead>
                              <tbody>
                                {item.orders.map((order) =>
                                  (order.items || []).map((orderItem, idx) => (
                                    <tr key={`${order.order_id}-${idx}`} className="border-t border-gray-100 hover:bg-gray-50">
                                      <td className="p-2 text-xs text-gray-600">
                                        {order.created_at ? format(new Date(order.created_at), 'MMM dd, HH:mm') : '-'}
                                      </td>
                                      <td className="p-2 font-medium">
                                        {(orderItem.product_name || '').replace('Happy Hour Jaba - ', '')}
                                      </td>
                                      <td className="p-2 text-center">{orderItem.quantity}</td>
                                      <td className="p-2 text-right font-bold">
                                        KES {((orderItem.quantity || 0) * (orderItem.price || 500)).toLocaleString()}
                                      </td>
                                      <td className="p-2 text-center">
                                        <Badge className={`text-xs ${
                                          order.status === 'fulfilled' ? 'bg-hh-green text-black' :
                                          order.status === 'pending' ? 'bg-yellow-400 text-black' :
                                          'bg-red-500 text-white'
                                        }`}>
                                          {order.status}
                                        </Badge>
                                      </td>
                                    </tr>
                                  ))
                                )}
                              </tbody>
                            </table>
                          </div>
                        )}
                      </div>

                      {/* Action Buttons */}
                      <div className="flex gap-2 mt-3 pt-3 border-t flex-wrap">
                        <Button
                          data-testid={`generate-invoice-${item.user.user_id}`}
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setAutoInvoiceUserId(item.user.user_id);
                            setShowAutoInvoiceDialog(true);
                          }}
                          className="flex-1 border-2 border-hh-green text-black bg-hh-green/10 text-sm min-w-[120px]"
                        >
                          <FileText className="w-3 h-3 mr-1" />
                          Generate Invoice
                        </Button>
                        <Button
                          data-testid={`share-report-${item.user.user_id}`}
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setReportUserId(item.user.user_id);
                            setShowShareReportDialog(true);
                          }}
                          className="flex-1 border-2 border-black text-sm min-w-[120px]"
                        >
                          <Send className="w-3 h-3 mr-1" />
                          Share Report
                        </Button>
                        <Button
                          data-testid={`delete-user-${item.user.user_id}`}
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setUserToDelete(item.user);
                            setShowDeleteUserDialog(true);
                          }}
                          className="border-2 border-red-500 text-red-500 hover:bg-red-50 text-sm"
                        >
                          <Trash2 className="w-3 h-3" />
                        </Button>
                      </div>
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
                  <Button
                    data-testid="add-backlog-btn"
                    size="sm"
                    onClick={() => setShowBacklogDialog(true)}
                    className="bg-hh-green text-black border-2 border-black shadow-brutal-sm text-xs"
                  >
                    <Plus className="w-3 h-3 mr-1" />
                    Starting Credit
                  </Button>
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
                      
                      <details className="mt-3" data-testid={`defaulter-orders-${item.user.user_id}`}>
                        <summary className="cursor-pointer text-sm font-medium text-gray-700 hover:text-black">
                          View {item.orders?.length || 0} order(s) breakdown
                        </summary>
                        <div className="mt-2 border-2 border-gray-200 rounded-lg overflow-hidden">
                          <table className="w-full text-sm">
                            <thead className="bg-red-900 text-white">
                              <tr>
                                <th className="p-2 text-left text-xs font-display uppercase">Order ID</th>
                                <th className="p-2 text-left text-xs font-display uppercase">Timestamp</th>
                                <th className="p-2 text-left text-xs font-display uppercase">Flavor</th>
                                <th className="p-2 text-center text-xs font-display uppercase">Qty</th>
                                <th className="p-2 text-right text-xs font-display uppercase">Amount</th>
                              </tr>
                            </thead>
                            <tbody>
                              {item.orders?.map((order) =>
                                (order.items || []).map((orderItem, idx) => (
                                  <tr key={`${order.order_id}-${idx}`} className="border-t border-gray-100 hover:bg-red-50">
                                    <td className="p-2 text-xs font-mono">{order.order_id}</td>
                                    <td className="p-2 text-xs text-gray-600">
                                      {order.created_at ? format(new Date(order.created_at), 'MMM dd, HH:mm') : '-'}
                                    </td>
                                    <td className="p-2 font-medium text-xs">
                                      {(orderItem.product_name || '').replace('Happy Hour Jaba - ', '')}
                                    </td>
                                    <td className="p-2 text-center text-xs">{orderItem.quantity}</td>
                                    <td className="p-2 text-right text-xs font-bold">
                                      KES {((orderItem.quantity || 0) * (orderItem.price || 500)).toLocaleString()}
                                    </td>
                                  </tr>
                                ))
                              )}
                            </tbody>
                          </table>
                        </div>
                      </details>

                      {/* Warning Actions */}
                      <div className="flex gap-2 mt-3 pt-3 border-t flex-wrap">
                        <Button
                          data-testid={`warn-overdue-${item.user.user_id}`}
                          size="sm"
                          variant="outline"
                          onClick={() => sendDefaulterWarning(item.user.user_id, 'overdue')}
                          className="flex-1 border-2 border-yellow-500 text-yellow-700 text-xs min-w-[90px]"
                        >
                          Overdue Notice
                        </Button>
                        <Button
                          data-testid={`warn-limit-${item.user.user_id}`}
                          size="sm"
                          variant="outline"
                          onClick={() => sendDefaulterWarning(item.user.user_id, 'limit_reached')}
                          className="flex-1 border-2 border-orange-500 text-orange-700 text-xs min-w-[90px]"
                        >
                          Limit Reached
                        </Button>
                        <Button
                          data-testid={`warn-suspended-${item.user.user_id}`}
                          size="sm"
                          variant="outline"
                          onClick={() => sendDefaulterWarning(item.user.user_id, 'suspended')}
                          className="flex-1 border-2 border-red-500 text-red-700 text-xs min-w-[90px]"
                        >
                          Suspended
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* PAYMENT VERIFICATION TAB */}
            <TabsContent value="payments" className="space-y-4">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-xl uppercase">Payment Verification</h2>
                <Button
                  data-testid="refresh-payments-btn"
                  size="sm"
                  variant="outline"
                  onClick={fetchPendingPayments}
                  className="border-2 border-black"
                >
                  <RefreshCw className="w-4 h-4 mr-1" />
                  Refresh
                </Button>
              </div>
              <p className="text-sm text-gray-500">
                Match customer transactions against your Airtel Money records: <strong>0733878020</strong>
              </p>
              
              {pendingPayments.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
                  <Check className="w-12 h-12 mx-auto text-hh-green mb-3" />
                  <p className="text-gray-500">No pending payment verifications</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {pendingPayments.map((pop) => (
                    <div
                      key={pop.pop_id}
                      data-testid={`payment-${pop.pop_id}`}
                      className={`p-4 border-2 rounded-lg shadow-brutal-sm ${
                        pop.status === 'verification_failed' 
                          ? 'border-red-500 bg-red-50' 
                          : 'border-yellow-500 bg-yellow-50'
                      }`}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div>
                          <p className="font-display font-bold text-sm">{pop.user_name}</p>
                          <p className="text-xs text-gray-600">{pop.user_email}</p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={pop.payment_type === 'full' ? 'bg-hh-green text-black' : 'bg-blue-500 text-white'}>
                            {pop.payment_type}
                          </Badge>
                          {pop.status === 'verification_failed' && (
                            <Badge className="bg-red-500 text-white">FAILED</Badge>
                          )}
                        </div>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
                        <div className="p-2 bg-white rounded border">
                          <p className="text-xs text-gray-500">Invoice</p>
                          <p className="font-mono font-bold text-xs">{pop.invoice_id}</p>
                        </div>
                        <div className="p-2 bg-white rounded border">
                          <p className="text-xs text-gray-500">Customer Amount</p>
                          <p className="font-display font-bold text-hh-green">KES {pop.amount_paid?.toLocaleString()}</p>
                        </div>
                        <div className="p-2 bg-white rounded border">
                          <p className="text-xs text-gray-500">Customer Code</p>
                          <p className="font-mono font-bold text-xs">{pop.transaction_code}</p>
                        </div>
                        <div className="p-2 bg-white rounded border">
                          <p className="text-xs text-gray-500">Method</p>
                          <p className="text-xs font-medium">{pop.payment_method?.replace('_', ' ')}</p>
                        </div>
                      </div>
                      
                      {pop.decline_reason && (
                        <div className="mb-3 p-2 bg-red-100 rounded border border-red-300 text-xs text-red-700">
                          <strong>Decline reason:</strong> {pop.decline_reason}
                        </div>
                      )}
                      
                      {pop.notes && (
                        <p className="text-xs text-gray-600 mb-3 p-2 bg-white rounded border italic">
                          Note: {pop.notes}
                        </p>
                      )}
                      
                      <p className="text-xs text-gray-400 mb-3">
                        Submitted: {pop.submitted_at ? format(new Date(pop.submitted_at), 'MMM dd, yyyy HH:mm') : '-'}
                      </p>
                      
                      <div className="flex gap-2 flex-wrap">
                        <Button
                          data-testid={`match-payment-${pop.pop_id}`}
                          size="sm"
                          onClick={() => {
                            setMatchingPop(pop);
                            setAdminTxCode('');
                            setAdminAmount('');
                            setShowMatchDialog(true);
                          }}
                          className="flex-1 bg-hh-green text-black border-2 border-black min-w-[80px]"
                        >
                          <Check className="w-3 h-3 mr-1" />
                          Match
                        </Button>
                        {pop.status === 'verification_failed' && (
                          <Button
                            data-testid={`force-approve-${pop.pop_id}`}
                            size="sm"
                            variant="outline"
                            onClick={() => {
                              setForceApprovePop(pop);
                              setForceApproveReason('');
                              setShowForceApproveDialog(true);
                            }}
                            className="flex-1 border-2 border-purple-500 text-purple-600 min-w-[80px]"
                          >
                            <Shield className="w-3 h-3 mr-1" />
                            Force Approve
                          </Button>
                        )}
                        <Button
                          data-testid={`reject-payment-${pop.pop_id}`}
                          size="sm"
                          variant="outline"
                          onClick={() => {
                            setVerifyingPayment(pop.pop_id);
                            setShowRejectDialog(true);
                          }}
                          className="border-2 border-red-500 text-red-500 min-w-[70px]"
                        >
                          <X className="w-3 h-3 mr-1" />
                          Reject
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>

            {/* CREDIT PURCHASE INVOICES TAB */}
            <TabsContent value="credit-invoices" className="space-y-4">
              <CreditInvoiceModule users={users} onRefresh={loadAllData} />
            </TabsContent>

            {/* MESSAGES / DISPUTE TAB */}
            <TabsContent value="messages" className="space-y-4">
              <h2 className="font-display text-xl uppercase">Dispute Messages</h2>
              <p className="text-sm text-gray-500">
                Customer inquiries linked to failed or disputed transactions
              </p>
              
              {disputes.length === 0 ? (
                <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg bg-white">
                  <Check className="w-12 h-12 mx-auto text-hh-green mb-3" />
                  <p className="text-gray-500">No active disputes</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {disputes.map((dispute) => (
                    <div
                      key={dispute.pop_id}
                      data-testid={`dispute-${dispute.pop_id}`}
                      className="p-4 border-2 border-orange-400 rounded-lg shadow-brutal-sm bg-orange-50 cursor-pointer hover:bg-orange-100 transition-colors"
                      onClick={() => openDisputeChat(dispute)}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <p className="font-display font-bold text-sm">{dispute.user_name}</p>
                          <p className="text-xs text-gray-500">
                            {dispute.pop_id} | Invoice: {dispute.invoice_id}
                          </p>
                        </div>
                        <div className="flex items-center gap-2">
                          <Badge className={
                            dispute.pop_status === 'verification_failed' ? 'bg-red-500 text-white' :
                            dispute.pop_status === 'approved' ? 'bg-hh-green text-black' :
                            'bg-yellow-400 text-black'
                          }>
                            {dispute.pop_status?.replace('_', ' ')}
                          </Badge>
                          <Badge className="bg-orange-500 text-white">
                            {dispute.message_count} msg
                          </Badge>
                        </div>
                      </div>
                      <p className="text-sm text-gray-700 truncate">
                        <span className="font-medium">{dispute.last_sender}:</span> {dispute.last_message}
                      </p>
                      <p className="text-xs text-gray-400 mt-1">
                        {dispute.last_time ? format(new Date(dispute.last_time), 'MMM dd, HH:mm') : ''}
                      </p>
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
            {/* MAINTENANCE TAB (Super Admin only) */}
            {isSuperAdmin && (
              <TabsContent value="maintenance" className="space-y-4">
                <h2 className="font-display text-xl uppercase text-purple-700">Maintenance Tools</h2>
                <p className="text-sm text-gray-500">
                  Super Admin controls for testing and data management. Use with caution.
                </p>

                <div className="grid gap-4 md:grid-cols-2">
                  {/* Reset All Test Data */}
                  <div className="p-6 border-2 border-red-500 rounded-lg bg-red-50">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 bg-red-500 rounded-lg flex items-center justify-center">
                        <Trash2 className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="font-display font-bold uppercase">Reset All Test Data</p>
                        <p className="text-xs text-gray-600">Clears ALL orders, invoices, payments, disputes, notifications</p>
                      </div>
                    </div>
                    <Button
                      data-testid="reset-all-data-btn"
                      onClick={resetAllTestData}
                      className="w-full bg-red-500 text-white border-2 border-red-700"
                    >
                      <Trash2 className="w-4 h-4 mr-2" />
                      Reset All Test Data
                    </Button>
                  </div>

                  {/* Reset Daily Counters */}
                  <div className="p-6 border-2 border-yellow-500 rounded-lg bg-yellow-50">
                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-10 h-10 bg-yellow-500 rounded-lg flex items-center justify-center">
                        <RefreshCw className="w-5 h-5 text-white" />
                      </div>
                      <div>
                        <p className="font-display font-bold uppercase">Reset Daily Counters</p>
                        <p className="text-xs text-gray-600">Removes today's orders to reset bottle count limit</p>
                      </div>
                    </div>
                    <Button
                      data-testid="reset-counters-btn"
                      onClick={resetDailyCounters}
                      className="w-full bg-yellow-500 text-black border-2 border-yellow-700"
                    >
                      <RefreshCw className="w-4 h-4 mr-2" />
                      Reset Daily Counters
                    </Button>
                  </div>
                </div>

                {/* System Info */}
                <div className="p-4 border-2 border-purple-300 rounded-lg bg-purple-50">
                  <p className="font-display text-sm uppercase font-bold text-purple-700 mb-2">System Info</p>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    <div className="p-2 bg-white rounded border">
                      <p className="text-xs text-gray-500">Role</p>
                      <p className="font-bold text-purple-600">{activeRole}</p>
                    </div>
                    <div className="p-2 bg-white rounded border">
                      <p className="text-xs text-gray-500">Email</p>
                      <p className="font-bold">{user?.email}</p>
                    </div>
                    <div className="p-2 bg-white rounded border">
                      <p className="text-xs text-gray-500">Daily Limit</p>
                      <p className="font-bold">{activeRole === 'super_admin' ? 'UNLIMITED' : '10 bottles'}</p>
                    </div>
                    <div className="p-2 bg-white rounded border">
                      <p className="text-xs text-gray-500">Credit Cap</p>
                      <p className="font-bold">{activeRole === 'super_admin' ? 'UNLIMITED' : 'KES 30,000'}</p>
                    </div>
                  </div>
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <div className="p-4 border-2 border-black rounded-lg bg-white shadow-brutal-sm space-y-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <p className="font-display text-sm uppercase font-bold">Approved Domains</p>
                        <p className="text-xs text-gray-500">Only active domains can sign in</p>
                      </div>
                      <Badge className="bg-black text-white">{approvedDomains.filter(domain => domain.is_active).length} active</Badge>
                    </div>
                    <div className="flex gap-2">
                      <Input
                        data-testid="approved-domain-input"
                        placeholder="example.com"
                        value={newApprovedDomain}
                        onChange={(e) => setNewApprovedDomain(e.target.value)}
                        className="border-2 border-black"
                      />
                      <Button
                        data-testid="add-approved-domain-btn"
                        onClick={addApprovedDomain}
                        className="bg-black text-white border-2 border-black"
                      >
                        Add
                      </Button>
                    </div>
                    <div className="space-y-3">
                      {approvedDomains.length === 0 ? (
                        <p className="text-sm text-gray-500">No managed domains yet</p>
                      ) : (
                        approvedDomains.map((domain) => (
                          <div key={domain.domain} className="flex items-center justify-between gap-3 p-3 border-2 border-black rounded-lg bg-gray-50">
                            <div>
                              <p className="font-display text-sm uppercase">{domain.domain}</p>
                              <p className="text-xs text-gray-500">
                                {domain.is_active ? `Added by ${domain.added_by || 'system'}` : `Disabled by ${domain.disabled_by || 'unknown'}`}
                              </p>
                            </div>
                            {domain.is_active ? (
                              <Button
                                data-testid={`disable-domain-${domain.domain}`}
                                size="sm"
                                variant="outline"
                                onClick={() => disableApprovedDomain(domain.domain)}
                                className="border-2 border-red-500 text-red-600"
                              >
                                Disable
                              </Button>
                            ) : (
                              <Badge className="bg-gray-300 text-black">Inactive</Badge>
                            )}
                          </div>
                        ))
                      )}
                    </div>
                  </div>

                  <div className="p-4 border-2 border-black rounded-lg bg-white shadow-brutal-sm space-y-4">
                    <div>
                      <p className="font-display text-sm uppercase font-bold">User Roles</p>
                      <p className="text-xs text-gray-500">Promote or demote users without redeploying</p>
                    </div>
                    <div className="space-y-3 max-h-[420px] overflow-y-auto pr-1">
                      {users.map((managedUser) => (
                        <div key={managedUser.user_id} className="p-3 border-2 border-black rounded-lg bg-gray-50 space-y-3">
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <p className="font-display text-sm uppercase">{managedUser.name}</p>
                              <p className="text-xs text-gray-500 break-all">{managedUser.email}</p>
                            </div>
                            <Badge className={
                              managedUser.role === 'super_admin' ? 'bg-purple-600 text-white' :
                              managedUser.role === 'admin' ? 'bg-hh-green text-black' :
                              'bg-gray-200 text-black'
                            }>
                              {managedUser.role.replace('_', ' ')}
                            </Badge>
                          </div>
                          <Select
                            value={managedUser.role}
                            onValueChange={(value) => updateUserRoleAssignment(managedUser.user_id, value)}
                            disabled={managedUser.user_id === user?.user_id || updatingUserRoleId === managedUser.user_id}
                          >
                            <SelectTrigger className="border-2 border-black bg-white">
                              <SelectValue placeholder="Assign role" />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="user">User</SelectItem>
                              <SelectItem value="admin">Admin</SelectItem>
                              <SelectItem value="super_admin">Super Admin</SelectItem>
                            </SelectContent>
                          </Select>
                          {managedUser.user_id === user?.user_id && (
                            <p className="text-xs text-gray-500">Your own role is locked here to avoid removing your current access.</p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              </TabsContent>
            )}
          </Tabs>
        </div>
      </main>

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

      {/* Share Reconciliation Report Dialog */}
      <Dialog open={showShareReportDialog} onOpenChange={(open) => {
        setShowShareReportDialog(open);
        if (!open) { setReportPreview(null); setReportStartDate(''); setReportEndDate(''); }
      }}>
        <DialogContent className="max-w-lg border-2 border-black shadow-brutal-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Share Reconciliation Report</DialogTitle>
            <DialogDescription>
              Send credit reconciliation report to {users.find(u => u.user_id === reportUserId)?.name || 'user'} via email and in-app notification
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label className="font-display uppercase text-sm">Start Date</Label>
                <Input
                  data-testid="report-start-date"
                  type="date"
                  value={reportStartDate}
                  onChange={(e) => setReportStartDate(e.target.value)}
                  className="border-2 border-black"
                />
              </div>
              <div>
                <Label className="font-display uppercase text-sm">End Date</Label>
                <Input
                  data-testid="report-end-date"
                  type="date"
                  value={reportEndDate}
                  onChange={(e) => setReportEndDate(e.target.value)}
                  className="border-2 border-black"
                />
              </div>
            </div>

            <Button
              data-testid="preview-report-btn"
              variant="outline"
              onClick={() => fetchReportPreview(reportUserId, reportStartDate, reportEndDate)}
              className="w-full border-2 border-black"
            >
              <Search className="w-4 h-4 mr-2" />
              Preview Report
            </Button>

            {/* Report Preview */}
            {reportPreview && (
              <div className="border-2 border-black rounded-lg overflow-hidden">
                <div className="p-3 bg-black text-white">
                  <p className="font-display font-bold text-hh-green">{reportPreview.user?.name}</p>
                  <p className="text-xs text-gray-300">{reportPreview.user?.email}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Period: {reportPreview.period?.start || 'All time'} — {reportPreview.period?.end || 'Present'}
                  </p>
                </div>
                <div className="p-3 space-y-2">
                  <div className="flex justify-between items-center p-2 bg-red-50 rounded border border-red-200">
                    <span className="text-sm font-medium">Outstanding Balance</span>
                    <span className="font-display font-bold text-red-600">
                      KES {(reportPreview.outstanding_balance || 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-2 bg-gray-50 rounded border">
                    <span className="text-sm font-medium">Total Credit Used</span>
                    <span className="font-display font-bold">
                      KES {(reportPreview.total_amount || 0).toLocaleString()}
                    </span>
                  </div>
                  <p className="text-xs text-gray-500">
                    {reportPreview.order_breakdown?.length || 0} order item(s) in period
                  </p>
                </div>
              </div>
            )}

            <Button
              data-testid="send-report-btn"
              onClick={shareReconciliationReport}
              className="w-full h-12 bg-hh-green text-black border-2 border-black shadow-brutal"
            >
              <Send className="w-4 h-4 mr-2" />
              Send Report to User
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Delete User Confirmation Dialog */}
      <Dialog open={showDeleteUserDialog} onOpenChange={(open) => {
        setShowDeleteUserDialog(open);
        if (!open) setUserToDelete(null);
      }}>
        <DialogContent className="max-w-sm border-2 border-red-500 shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase text-red-600">Delete User</DialogTitle>
            <DialogDescription>
              This action cannot be undone. All data for this user will be permanently deleted.
            </DialogDescription>
          </DialogHeader>
          {userToDelete && (
            <div className="space-y-4">
              <div className="p-4 bg-red-50 border-2 border-red-200 rounded-lg">
                <p className="font-bold">{userToDelete.name}</p>
                <p className="text-sm text-gray-600">{userToDelete.email}</p>
                <p className="text-sm text-gray-600">{userToDelete.phone}</p>
              </div>
              <p className="text-sm text-gray-600">
                This will delete the user account, all their orders, notifications, and invoices.
              </p>
              <div className="flex gap-2">
                <Button
                  data-testid="cancel-delete-user-btn"
                  variant="outline"
                  onClick={() => { setShowDeleteUserDialog(false); setUserToDelete(null); }}
                  className="flex-1 border-2 border-black"
                >
                  Cancel
                </Button>
                <Button
                  data-testid="confirm-delete-user-btn"
                  onClick={() => { deleteUser(userToDelete.user_id); setShowDeleteUserDialog(false); }}
                  className="flex-1 bg-red-500 text-white border-2 border-red-700"
                >
                  <Trash2 className="w-4 h-4 mr-1" />
                  Delete User
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Starting Credit Import Dialog */}
      <Dialog open={showBacklogDialog} onOpenChange={(open) => {
        setShowBacklogDialog(open);
        if (!open) { setBacklogUserId(''); setBacklogAmount(''); setBacklogDescription(''); }
      }}>
        <DialogContent className="max-w-md border-2 border-black shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Import Starting Credit</DialogTitle>
            <DialogDescription>Add a legacy opening credit usage amount so tracking is accurate going forward</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label className="font-display uppercase text-sm">Customer *</Label>
              <Select value={backlogUserId} onValueChange={setBacklogUserId}>
                <SelectTrigger data-testid="backlog-user-select" className="border-2 border-black">
                  <SelectValue placeholder="Select customer" />
                </SelectTrigger>
                <SelectContent>
                  {users.filter(u => u.role !== 'admin').map(u => (
                    <SelectItem key={u.user_id} value={u.user_id}>
                      {u.name} ({u.email})
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="font-display uppercase text-sm">Starting Usage Amount (KES) *</Label>
              <Input
                data-testid="backlog-amount"
                type="number"
                value={backlogAmount}
                onChange={(e) => setBacklogAmount(e.target.value)}
                className="border-2 border-black"
                placeholder="e.g. 25000"
              />
            </div>
            <div>
              <Label className="font-display uppercase text-sm">Legacy Notes *</Label>
              <Textarea
                data-testid="backlog-description"
                value={backlogDescription}
                onChange={(e) => setBacklogDescription(e.target.value)}
                className="border-2 border-black"
                placeholder="e.g. Imported from offline ledger up to February 2026"
              />
            </div>
            <Button
              data-testid="submit-backlog-btn"
              onClick={submitBacklogCredit}
              className="w-full h-12 bg-hh-green text-black border-2 border-black shadow-brutal"
            >
              Import Starting Credit
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Payment Reject Dialog */}
      <Dialog open={showRejectDialog} onOpenChange={(open) => {
        setShowRejectDialog(open);
        if (!open) { setVerifyingPayment(null); setVerifyRejectReason(''); }
      }}>
        <DialogContent className="max-w-sm border-2 border-red-500 shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase text-red-600">Reject Payment</DialogTitle>
            <DialogDescription>Provide a reason for rejecting this payment proof</DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <Textarea
              data-testid="reject-reason-input"
              value={verifyRejectReason}
              onChange={(e) => setVerifyRejectReason(e.target.value)}
              className="border-2 border-black min-h-[100px]"
              placeholder="e.g. Transaction code not found, amount mismatch, duplicate submission..."
            />
            <div className="flex gap-2">
              <Button
                variant="outline"
                onClick={() => { setShowRejectDialog(false); setVerifyingPayment(null); }}
                className="flex-1 border-2 border-black"
              >
                Cancel
              </Button>
              <Button
                data-testid="confirm-reject-payment-btn"
                onClick={rejectPayment}
                className="flex-1 bg-red-500 text-white border-2 border-red-700"
              >
                Reject Payment
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Transaction Match Dialog */}
      <Dialog open={showMatchDialog} onOpenChange={(open) => {
        setShowMatchDialog(open);
        if (!open) { setMatchingPop(null); setAdminTxCode(''); setAdminAmount(''); }
      }}>
        <DialogContent className="max-w-md border-2 border-black shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase">Match Transaction</DialogTitle>
            <DialogDescription>
              Enter the transaction details from your Airtel Money records
            </DialogDescription>
          </DialogHeader>
          {matchingPop && (
            <div className="space-y-4">
              {/* Customer's Entry (read-only) */}
              <div className="p-3 bg-gray-50 border-2 border-gray-200 rounded-lg">
                <p className="text-xs text-gray-500 font-display uppercase mb-2">Customer Entry</p>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-xs text-gray-500">Code</p>
                    <p className="font-mono font-bold">{matchingPop.transaction_code}</p>
                  </div>
                  <div>
                    <p className="text-xs text-gray-500">Amount</p>
                    <p className="font-display font-bold">KES {matchingPop.amount_paid?.toLocaleString()}</p>
                  </div>
                </div>
              </div>

              {/* Admin's Entry */}
              <div className="p-3 bg-hh-green/10 border-2 border-hh-green rounded-lg space-y-3">
                <p className="text-xs text-gray-700 font-display uppercase">Your Records (Airtel Money)</p>
                <div>
                  <Label className="font-display uppercase text-sm">Transaction Code *</Label>
                  <Input
                    data-testid="admin-tx-code"
                    value={adminTxCode}
                    onChange={(e) => setAdminTxCode(e.target.value.toUpperCase())}
                    className="border-2 border-black uppercase"
                    placeholder="Enter code from your records"
                  />
                </div>
                <div>
                  <Label className="font-display uppercase text-sm">Amount (KES) *</Label>
                  <Input
                    data-testid="admin-tx-amount"
                    type="number"
                    value={adminAmount}
                    onChange={(e) => setAdminAmount(e.target.value)}
                    className="border-2 border-black"
                    placeholder="Enter amount from records"
                  />
                </div>
              </div>

              <Button
                data-testid="submit-match-btn"
                onClick={matchTransaction}
                className="w-full h-12 bg-hh-green text-black border-2 border-black shadow-brutal"
              >
                <Check className="w-4 h-4 mr-2" />
                Verify Match
              </Button>
              <p className="text-xs text-gray-500 text-center">
                If codes and amounts match, payment is auto-approved. Mismatches will be flagged.
              </p>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Force Approve Dialog */}
      <Dialog open={showForceApproveDialog} onOpenChange={(open) => {
        setShowForceApproveDialog(open);
        if (!open) { setForceApprovePop(null); setForceApproveReason(''); }
      }}>
        <DialogContent className="max-w-md border-2 border-purple-500 shadow-brutal-lg">
          <DialogHeader>
            <DialogTitle className="font-display text-xl uppercase text-purple-700">Force Approve</DialogTitle>
            <DialogDescription>
              Override automated check and manually approve this payment. An audit trail will be recorded.
            </DialogDescription>
          </DialogHeader>
          {forceApprovePop && (
            <div className="space-y-4">
              <div className="p-3 bg-purple-50 border-2 border-purple-200 rounded-lg text-sm">
                <p><strong>POP:</strong> {forceApprovePop.pop_id}</p>
                <p><strong>Customer:</strong> {forceApprovePop.user_name}</p>
                <p><strong>Code:</strong> {forceApprovePop.transaction_code}</p>
                <p><strong>Amount:</strong> KES {forceApprovePop.amount_paid?.toLocaleString()}</p>
                {forceApprovePop.decline_reason && (
                  <p className="text-red-600 mt-2"><strong>Original decline:</strong> {forceApprovePop.decline_reason}</p>
                )}
              </div>
              
              <div>
                <Label className="font-display uppercase text-sm">Reason for Manual Override *</Label>
                <Textarea
                  data-testid="force-approve-reason"
                  value={forceApproveReason}
                  onChange={(e) => setForceApproveReason(e.target.value)}
                  className="border-2 border-black min-h-[100px]"
                  placeholder="e.g. Verified via direct call with customer, amount difference is bank charge, etc."
                />
              </div>
              
              <Button
                data-testid="confirm-force-approve-btn"
                onClick={forceApprovePayment}
                className="w-full h-12 bg-purple-600 text-white border-2 border-purple-800"
              >
                <Shield className="w-4 h-4 mr-2" />
                Force Approve Payment
              </Button>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Dispute Chat Dialog */}
      <Dialog open={showDisputeChat} onOpenChange={(open) => {
        setShowDisputeChat(open);
        if (!open) { setSelectedDispute(null); setDisputeMessages([]); setNewDisputeMsg(''); }
      }}>
        <DialogContent className="max-w-lg border-2 border-orange-400 shadow-brutal-lg max-h-[85vh] flex flex-col">
          <DialogHeader>
            <DialogTitle className="font-display text-lg uppercase">
              Dispute: {selectedDispute?.pop_id}
            </DialogTitle>
            <DialogDescription>
              {selectedDispute?.user_name} | Invoice: {selectedDispute?.invoice_id} | Status: {selectedDispute?.pop_status?.replace('_', ' ')}
            </DialogDescription>
          </DialogHeader>
          
          {/* Chat Messages */}
          <div className="flex-1 overflow-y-auto space-y-2 p-2 bg-gray-50 rounded-lg border min-h-[200px] max-h-[300px]">
            {disputeMessages.length === 0 ? (
              <p className="text-center text-gray-400 text-sm py-8">No messages yet</p>
            ) : (
              disputeMessages.map((msg) => (
                <div
                  key={msg.message_id}
                  data-testid={`msg-${msg.message_id}`}
                  className={`p-2 rounded-lg max-w-[85%] ${
                    msg.sender_role === 'admin' 
                      ? 'ml-auto bg-hh-green text-black border border-green-600' 
                      : 'bg-white border border-gray-300'
                  }`}
                >
                  <p className="text-xs font-bold mb-1">
                    {msg.sender_role === 'admin' ? 'Admin' : msg.sender_name}
                  </p>
                  <p className="text-sm">{msg.message}</p>
                  <p className="text-xs text-gray-500 mt-1">
                    {msg.created_at ? format(new Date(msg.created_at), 'MMM dd, HH:mm') : ''}
                  </p>
                </div>
              ))
            )}
          </div>
          
          {/* Reply input */}
          <div className="flex gap-2 mt-2">
            <Input
              data-testid="dispute-reply-input"
              value={newDisputeMsg}
              onChange={(e) => setNewDisputeMsg(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && sendAdminReply()}
              className="flex-1 border-2 border-black"
              placeholder="Type admin reply..."
            />
            <Button
              data-testid="send-dispute-reply-btn"
              onClick={sendAdminReply}
              className="bg-hh-green text-black border-2 border-black"
            >
              <Send className="w-4 h-4" />
            </Button>
          </div>
          
          {/* Force Approve shortcut */}
          {selectedDispute?.pop_status === 'verification_failed' && (
            <Button
              data-testid="chat-force-approve-btn"
              onClick={() => {
                setShowDisputeChat(false);
                setForceApprovePop({
                  pop_id: selectedDispute.pop_id,
                  user_name: selectedDispute.user_name,
                  transaction_code: selectedDispute.transaction_code,
                  amount_paid: selectedDispute.amount_paid
                });
                setForceApproveReason('');
                setShowForceApproveDialog(true);
              }}
              variant="outline"
              className="w-full border-2 border-purple-500 text-purple-600"
            >
              <Shield className="w-4 h-4 mr-2" />
              Resolve & Force Approve
            </Button>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AdminDashboard;
