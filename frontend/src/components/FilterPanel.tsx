import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { XMarkIcon } from '@heroicons/react/24/outline';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000';

interface FilterPanelProps {
  filters: any;
  updateFilter: (key: string, value: any) => void;
  clearFilters: () => void;
  activeFilterCount: number;
}

interface Vendor {
  id: number;
  name: string;
}

export default function FilterPanel({ filters, updateFilter, clearFilters, activeFilterCount }: FilterPanelProps) {
  const [vendors, setVendors] = useState<Vendor[]>([]);

  useEffect(() => {
    fetchVendors();
  }, []);

  const fetchVendors = async () => {
    try {
      const response = await axios.get(`${API_BASE}/api/vendors`);
      setVendors(response.data);
    } catch (error) {
      console.error('Error fetching vendors:', error);
    }
  };

  return (
    <div className="bg-slate-800/50 rounded-lg p-4 space-y-4 border border-slate-700">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-white font-semibold">Advanced Filters</h3>
        {activeFilterCount > 0 && (
          <button
            onClick={clearFilters}
            className="flex items-center gap-1 text-sm text-slate-400 hover:text-red-400 transition"
          >
            <XMarkIcon className="w-4 h-4" />
            Clear All
          </button>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Vendor Filter */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Vendor
          </label>
          <select
            value={filters.vendor_id || ''}
            onChange={(e) => updateFilter('vendor_id', e.target.value ? parseInt(e.target.value) : undefined)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            <option value="">All Vendors</option>
            {vendors.map(vendor => (
              <option key={vendor.id} value={vendor.id}>
                {vendor.name}
              </option>
            ))}
          </select>
        </div>

        {/* Min Price */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Min Price
          </label>
          <input
            type="number"
            min="0"
            step="1"
            placeholder="$0"
            value={filters.min_price || ''}
            onChange={(e) => updateFilter('min_price', e.target.value ? parseFloat(e.target.value) : undefined)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>

        {/* Max Price */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Max Price
          </label>
          <input
            type="number"
            min="0"
            step="1"
            placeholder="$999"
            value={filters.max_price || ''}
            onChange={(e) => updateFilter('max_price', e.target.value ? parseFloat(e.target.value) : undefined)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-green-500"
          />
        </div>

        {/* Product Type */}
        <div>
          <label className="block text-sm font-medium text-slate-300 mb-2">
            Product Type
          </label>
          <select
            value={filters.product_type || ''}
            onChange={(e) => updateFilter('product_type', e.target.value || undefined)}
            className="w-full px-3 py-2 bg-slate-900 border border-slate-700 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-green-500"
          >
            <option value="">All Types</option>
            <option value="flower">Flower</option>
            <option value="live_resin">Live Resin</option>
            <option value="live_rosin">Live Rosin</option>
            <option value="rosin">Rosin</option>
            <option value="shatter">Shatter</option>
            <option value="wax">Wax</option>
            <option value="crumble">Crumble</option>
            <option value="budder">Budder</option>
            <option value="sauce">Sauce</option>
            <option value="diamonds">Diamonds</option>
            <option value="bubble_hash">Bubble Hash</option>
            <option value="dry_sift">Dry Sift</option>
            <option value="vape_cart">Vape Cart</option>
            <option value="disposable">Disposable</option>
          </select>
        </div>
      </div>

      {/* Price Range Slider (Optional Enhancement) */}
      <div className="pt-2">
        <label className="block text-sm font-medium text-slate-300 mb-2">
          Price Range: ${filters.min_price || 0} - ${filters.max_price || 999}
        </label>
        <div className="flex gap-4 items-center">
          <input
            type="range"
            min="0"
            max="500"
            step="5"
            value={filters.min_price || 0}
            onChange={(e) => updateFilter('min_price', parseFloat(e.target.value))}
            className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
          <input
            type="range"
            min="0"
            max="500"
            step="5"
            value={filters.max_price || 500}
            onChange={(e) => updateFilter('max_price', parseFloat(e.target.value))}
            className="flex-1 h-2 bg-slate-700 rounded-lg appearance-none cursor-pointer accent-green-500"
          />
        </div>
      </div>

      {/* Active Filters Display */}
      {activeFilterCount > 0 && (
        <div className="flex flex-wrap gap-2 pt-2 border-t border-slate-700">
          {filters.vendor_id && (
            <FilterBadge
              label={`Vendor: ${vendors.find(v => v.id === filters.vendor_id)?.name}`}
              onRemove={() => updateFilter('vendor_id', undefined)}
            />
          )}
          {filters.product_type && (
            <FilterBadge
              label={`Type: ${filters.product_type.replace('_', ' ')}`}
              onRemove={() => updateFilter('product_type', undefined)}
            />
          )}
          {(filters.min_price || filters.max_price) && (
            <FilterBadge
              label={`Price: $${filters.min_price || 0} - $${filters.max_price || '999+'}`}
              onRemove={() => {
                updateFilter('min_price', undefined);
                updateFilter('max_price', undefined);
              }}
            />
          )}
          {filters.is_new && (
            <FilterBadge
              label="New Drops"
              onRemove={() => updateFilter('is_new', undefined)}
            />
          )}
          {filters.is_deal && (
            <FilterBadge
              label="Best Deals"
              onRemove={() => updateFilter('is_deal', undefined)}
            />
          )}
        </div>
      )}
    </div>
  );
}

function FilterBadge({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 px-3 py-1 bg-green-600/20 border border-green-600/30 text-green-400 rounded-full text-sm">
      {label}
      <button
        onClick={onRemove}
        className="hover:bg-green-600/30 rounded-full p-0.5 transition"
      >
        <XMarkIcon className="w-3 h-3" />
      </button>
    </span>
  );
}
