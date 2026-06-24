import { Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Home from './pages/Home';
import SearchPage from './pages/SearchPage';
import WatchlistPage from './pages/WatchlistPage';

export default function App() {
  return (
    <div className="app">
      <Navbar />
      <Routes>
        <Route path="/"          element={<Home />} />
        <Route path="/search"    element={<SearchPage />} />
        <Route path="/watchlist" element={<WatchlistPage />} />
      </Routes>
    </div>
  );
}
