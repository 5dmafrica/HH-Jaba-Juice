import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import axios from 'axios';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { Beer, ArrowLeft, Bell, Gift, FileText, Check, Mail } from 'lucide-react';
import { toast } from 'sonner';
import { format } from 'date-fns';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const Notifications = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchNotifications();
  }, []);

  const fetchNotifications = async () => {
    setLoading(true);
    try {
      const response = await axios.get(`${API}/notifications`, { withCredentials: true });
      setNotifications(response.data);
    } catch (error) {
      toast.error('Failed to load notifications');
    } finally {
      setLoading(false);
    }
  };

  const markAsRead = async (notificationId) => {
    try {
      await axios.put(`${API}/notifications/${notificationId}/read`, {}, { withCredentials: true });
      setNotifications(prev => prev.map(n => 
        n.notification_id === notificationId ? { ...n, read: true } : n
      ));
    } catch (error) {
      console.error('Failed to mark as read');
    }
  };

  const getNotificationIcon = (type) => {
    switch (type) {
      case 'offer':
        return <Gift className="w-5 h-5 text-purple-600" />;
      case 'invoice':
        return <FileText className="w-5 h-5 text-blue-600" />;
      case 'order':
        return <Beer className="w-5 h-5 text-hh-green" />;
      default:
        return <Bell className="w-5 h-5 text-gray-600" />;
    }
  };

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
              <Bell className="w-6 h-6 text-hh-green" />
            </div>
            <h1 className="font-display text-xl font-bold uppercase tracking-tight text-black">
              Notifications
            </h1>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 p-4">
        <div className="max-w-md mx-auto space-y-3">
          {loading ? (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-2 border-black border-t-hh-green rounded-full animate-spin mx-auto"></div>
            </div>
          ) : notifications.length === 0 ? (
            <div className="text-center py-12 border-2 border-dashed border-gray-300 rounded-lg">
              <Bell className="w-12 h-12 mx-auto text-gray-400 mb-3" />
              <p className="text-gray-500">No notifications yet</p>
            </div>
          ) : (
            notifications.map((notification) => (
              <div
                key={notification.notification_id}
                data-testid={`notification-${notification.notification_id}`}
                className={`p-4 border-2 border-black rounded-lg shadow-brutal-sm cursor-pointer transition-colors ${
                  notification.read ? 'bg-gray-50' : 'bg-white'
                }`}
                onClick={() => !notification.read && markAsRead(notification.notification_id)}
              >
                <div className="flex items-start gap-3">
                  <div className={`w-10 h-10 rounded-full flex items-center justify-center ${
                    notification.notification_type === 'offer' ? 'bg-purple-100' :
                    notification.notification_type === 'invoice' ? 'bg-blue-100' :
                    'bg-gray-100'
                  }`}>
                    {getNotificationIcon(notification.notification_type)}
                  </div>
                  <div className="flex-1">
                    <div className="flex items-start justify-between">
                      <p className="font-display font-bold text-sm">{notification.title}</p>
                      {!notification.read && (
                        <Badge className="bg-red-500 text-white text-xs">NEW</Badge>
                      )}
                    </div>
                    <p className="text-sm text-gray-600 mt-1">{notification.message}</p>
                    <p className="text-xs text-gray-400 mt-2">
                      {format(new Date(notification.created_at), 'MMM dd, yyyy • HH:mm')}
                    </p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
};

export default Notifications;
