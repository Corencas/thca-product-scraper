import React from 'react';
import { 
  ArrowTopRightOnSquareIcon, 
  FireIcon,
  SparklesIcon,
  CheckCircleIcon,
  XCircleIcon 
} from '@heroicons/react/24/outline';

interface Product {
  id: number;
  title: string;
  url: string;
  image_url?: string;
  vendor_name: string;
  strain_name?: string;
  product_type: string;
  current_price?: number;
  weight_grams?: number;
  price_per_gram?: number;
  thca_percentage?: number;
  in_stock: boolean;
  is_new: boolean;
  is_deal: boolean;
  first_seen: string;
}

interface ProductCardProps {
  product: Product;
}

export default function ProductCard({ product }: ProductCardProps) {
  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const getProductTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      'flower': 'bg-green-500/10 text-green-400 border-green-500/20',
      'live_resin': 'bg-orange-500/10 text-orange-400 border-orange-500/20',
      'live_rosin': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
      'rosin': 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
      'shatter': 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      'sauce': 'bg-purple-500/10 text-purple-400 border-purple-500/20',
      'diamonds': 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      'bubble_hash': 'bg-teal-500/10 text-teal-400 border-teal-500/20',
    };
    return colors[type.toLowerCase()] || 'bg-slate-500/10 text-slate-400 border-slate-500/20';
  };

  return (
    <div className="group bg-slate-900 rounded-xl overflow-hidden border border-slate-800 hover:border-green-500/50 transition-all duration-300 hover:shadow-xl hover:shadow-green-500/10 flex flex-col h-full">
      {/* Image */}
      <div className="relative aspect-square bg-slate-800 overflow-hidden">
        {product.image_url ? (
          <img
            src={product.image_url}
            alt={product.title}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-600">
            <div className="text-center">
              <div className="text-6xl mb-2">🌿</div>
              <div className="text-sm">No image</div>
            </div>
          </div>
        )}
        
        {/* Badges */}
        <div className="absolute top-2 left-2 flex flex-col gap-1">
          {product.is_new && (
            <span className="px-2 py-1 bg-green-500 text-white text-xs font-bold rounded-full flex items-center gap-1">
              <SparklesIcon className="w-3 h-3" />
              NEW
            </span>
          )}
          {product.is_deal && (
            <span className="px-2 py-1 bg-orange-500 text-white text-xs font-bold rounded-full flex items-center gap-1">
              <FireIcon className="w-3 h-3" />
              DEAL
            </span>
          )}
        </div>

        {/* Stock Status */}
        <div className="absolute top-2 right-2">
          {product.in_stock ? (
            <span className="px-2 py-1 bg-green-900/90 backdrop-blur-sm text-green-300 text-xs font-medium rounded-full flex items-center gap-1">
              <CheckCircleIcon className="w-3 h-3" />
              In Stock
            </span>
          ) : (
            <span className="px-2 py-1 bg-red-900/90 backdrop-blur-sm text-red-300 text-xs font-medium rounded-full flex items-center gap-1">
              <XCircleIcon className="w-3 h-3" />
              Out of Stock
            </span>
          )}
        </div>
      </div>

      {/* Content */}
      <div className="p-4 flex flex-col flex-1">
        {/* Vendor */}
        <div className="flex items-center justify-between mb-2">
          <span className="text-xs font-medium text-green-400">
            {product.vendor_name}
          </span>
          <span className="text-xs text-slate-500">
            {formatDate(product.first_seen)}
          </span>
        </div>

        {/* Title */}
        <h3 className="text-white font-semibold mb-2 line-clamp-2 group-hover:text-green-400 transition min-h-[2.5rem]">
          {product.title}
        </h3>

        {/* Strain Name */}
        {product.strain_name && (
          <div className="text-sm text-slate-400 mb-2">
            Strain: <span className="text-green-400">{product.strain_name}</span>
          </div>
        )}

        {/* Product Type */}
        <div className="mb-3">
          <span className={`inline-flex px-2 py-1 rounded-md text-xs font-medium border ${getProductTypeColor(product.product_type)}`}>
            {product.product_type.replace(/_/g, ' ').toUpperCase()}
          </span>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-2 mb-3 text-sm">
          {product.current_price && (
            <div className="bg-slate-800/50 rounded-lg p-2">
              <div className="text-slate-500 text-xs">Price</div>
              <div className="text-white font-bold">${product.current_price.toFixed(2)}</div>
            </div>
          )}
          {product.price_per_gram && (
            <div className="bg-slate-800/50 rounded-lg p-2">
              <div className="text-slate-500 text-xs">Per Gram</div>
              <div className="text-green-400 font-bold">${product.price_per_gram.toFixed(2)}/g</div>
            </div>
          )}
          {product.thca_percentage && (
            <div className="bg-slate-800/50 rounded-lg p-2">
              <div className="text-slate-500 text-xs">THCA</div>
              <div className="text-purple-400 font-bold">{product.thca_percentage.toFixed(1)}%</div>
            </div>
          )}
          {product.weight_grams && (
            <div className="bg-slate-800/50 rounded-lg p-2">
              <div className="text-slate-500 text-xs">Weight</div>
              <div className="text-slate-300 font-bold">{product.weight_grams}g</div>
            </div>
          )}
        </div>

        {/* Action Button */}
        <a
          href={product.url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-auto w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-green-600 hover:bg-green-700 text-white font-medium rounded-lg transition group"
        >
          <span>View Product</span>
          <ArrowTopRightOnSquareIcon className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition" />
        </a>
      </div>
    </div>
  );
}
