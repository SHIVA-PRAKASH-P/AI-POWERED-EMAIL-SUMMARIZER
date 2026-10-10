import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AppLayout } from './components/layout/AppLayout';
import { DashboardPage } from './pages/DashboardPage';
import { InboxPage } from './pages/InboxPage';
import { EmailDetailPage } from './pages/EmailDetailPage';
import { PriorityPage } from './pages/PriorityPage';
import { DeadlinesPage } from './pages/DeadlinesPage';
import { MeetingsPage } from './pages/MeetingsPage';
import { ActionItemsPage } from './pages/ActionItemsPage';
import { SettingsPage } from './pages/SettingsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<AppLayout />}>
          <Route index element={<DashboardPage />} />
          <Route path="inbox" element={<InboxPage />} />
          <Route path="emails/:id" element={<EmailDetailPage />} />
          <Route path="priority" element={<PriorityPage />} />
          <Route path="deadlines" element={<DeadlinesPage />} />
          <Route path="meetings" element={<MeetingsPage />} />
          <Route path="action-items" element={<ActionItemsPage />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
