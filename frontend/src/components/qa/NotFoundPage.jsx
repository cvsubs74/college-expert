import React from 'react';
import { Link } from 'react-router-dom';

// Generic 404 page used as the AdminGate fallback. Looks like a normal
// "page not found" — no hint that an admin route exists at this URL.
const NotFoundPage = () => (
    <div className="min-h-screen flex items-center justify-center bg-[#FDFCF7] px-6 text-center">
        <div>
            <h1 className="text-6xl font-bold text-[#1A4D2E] mb-2">404</h1>
            <p className="text-lg text-[#4A4A4A] mb-6">Page not found.</p>
            <Link
                to="/"
                className="inline-block px-5 py-2.5 bg-[#1A4D2E] text-white font-semibold rounded-full hover:bg-[#2D6B45] transition-all shadow-md"
            >
                Back home
            </Link>
        </div>
    </div>
);

export default NotFoundPage;
