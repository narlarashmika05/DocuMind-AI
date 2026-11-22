import { BrowserRouter, Route, Routes } from 'react-router'
import AuthProvider from './context/AuthProvider'
import AppLayout from './layouts/AppLayout'
import ChatPage from './pages/ChatPage'
import DashboardPage from './pages/DashboardPage'
import DocumentDetailPage from './pages/DocumentDetailPage'
import DocumentsPage from './pages/DocumentsPage'
import EvaluationPage from './pages/EvaluationPage'
import HomePage from './pages/HomePage'
import LoginPage from './pages/LoginPage'
import NotFoundPage from './pages/NotFoundPage'
import ProfilePage from './pages/ProfilePage'
import RegisterPage from './pages/RegisterPage'
import SearchPage from './pages/SearchPage'
import GuestRoute from './routes/GuestRoute'
import ProtectedRoute from './routes/ProtectedRoute'

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/" element={<HomePage />} />

          <Route element={<GuestRoute />}>
            <Route path="/login" element={<LoginPage />} />
            <Route path="/register" element={<RegisterPage />} />
          </Route>

          <Route element={<ProtectedRoute />}>
            <Route element={<AppLayout />}>
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/documents" element={<DocumentsPage />} />
              <Route path="/documents/:id" element={<DocumentDetailPage />} />
              <Route path="/chat" element={<ChatPage />} />
              <Route path="/chat/:conversationId" element={<ChatPage />} />
              <Route path="/search" element={<SearchPage />} />
              <Route path="/evaluation" element={<EvaluationPage />} />
              <Route path="/profile" element={<ProfilePage />} />
            </Route>
          </Route>

          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}
