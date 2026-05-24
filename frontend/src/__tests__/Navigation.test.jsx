/**
 * Navigation — mobile overflow regression test (issue #133).
 *
 * The logo is 2816×1536px (aspect ~1.83:1). At h-32 (128px), w-auto produces
 * ~234px of intrinsic width — wider than a 390px viewport when combined with
 * auth-action buttons. Fix: responsive height h-10 sm:h-32 + max-w-[120px]
 * sm:max-w-none on the img, and h-16 sm:h-36 on the nav row.
 *
 * jsdom has no layout engine, so we assert class presence (which is the CSS
 * contract that Tailwind enforces) rather than computed pixel widths.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import Navigation from '../components/Navigation';

// AuthContext is globally mocked in setup.js.
// PaymentContext is NOT used in Navigation — no additional mock needed.

// Wrap in MemoryRouter because Navigation uses <Link> and useLocation().
function renderNav() {
    return render(
        <MemoryRouter initialEntries={['/profile']}>
            <Navigation />
        </MemoryRouter>,
    );
}

describe('Navigation — mobile overflow (issue #133)', () => {
    it('logo img has mobile-constraining classes (h-10 sm:h-32 max-w-[120px])', () => {
        renderNav();
        const logo = screen.getByRole('img', { name: /stratia/i });
        // These classes must be present to prevent overflow at 390px viewport.
        // h-10 caps height at 40px on mobile; max-w-[120px] caps width.
        // sm:h-32 restores the full height on desktop (≥640px).
        expect(logo.className).toContain('h-10');
        expect(logo.className).toContain('max-w-[120px]');
        expect(logo.className).toContain('sm:h-32');
    });

    it('nav row has mobile-constraining height class (h-16 sm:h-36)', () => {
        const { container } = renderNav();
        // The inner flex row that controls nav height.
        const navRow = container.querySelector('.h-16');
        expect(navRow).not.toBeNull();
        expect(navRow.className).toContain('sm:h-36');
    });
});
